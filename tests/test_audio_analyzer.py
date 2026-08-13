"""Unit test suite for AudioAnalyzer time-domain audio analysis engine."""

import math
import unittest
from src.media.audio_capture import AudioFrame
from src.media.audio_analyzer import AudioAnalyzer


class TestAudioAnalyzer(unittest.TestCase):
    """Test suite covering initialization, input validation, attack/decay, multi-channel, and clamping."""

    def test_initialization_defaults(self) -> None:
        """Verify default initialization parameters and property accessors."""
        analyzer = AudioAnalyzer()
        self.assertEqual(analyzer.bar_count, 5)
        self.assertEqual(analyzer.min_baseline, 0.05)
        self.assertEqual(analyzer.attack_factor, 0.6)
        self.assertEqual(analyzer.decay_factor, 0.15)
        self.assertEqual(analyzer.sensitivity, 1.0)
        self.assertEqual(len(analyzer.current_bars), 5)
        self.assertTrue(all(b == 0.05 for b in analyzer.current_bars))

    def test_custom_configuration(self) -> None:
        """Verify custom configuration parameters."""
        analyzer = AudioAnalyzer(
            bar_count=8,
            attack_factor=0.8,
            decay_factor=0.2,
            min_baseline=0.1,
            sensitivity=1.5,
        )
        self.assertEqual(analyzer.bar_count, 8)
        self.assertEqual(analyzer.attack_factor, 0.8)
        self.assertEqual(analyzer.decay_factor, 0.2)
        self.assertEqual(analyzer.min_baseline, 0.1)
        self.assertEqual(analyzer.sensitivity, 1.5)
        self.assertEqual(len(analyzer.current_bars), 8)

    def test_silence_input(self) -> None:
        """Verify silence input (all 0.0 floats) produces baseline output."""
        analyzer = AudioAnalyzer(bar_count=5, min_baseline=0.05)
        samples = [0.0] * 480
        frame = AudioFrame(samples=samples, sample_rate=48000, channels=2, frame_count=240)

        bars = analyzer.process_frame(frame)
        self.assertEqual(len(bars), 5)
        self.assertTrue(all(b == 0.05 for b in bars))

    def test_zero_amplitude_input(self) -> None:
        """Verify zero-amplitude input maintains baseline or decays to baseline."""
        analyzer = AudioAnalyzer(bar_count=4, min_baseline=0.05)
        frame = AudioFrame(samples=[0.0] * 100, sample_rate=44100, channels=1, frame_count=100)
        bars = analyzer.process_frame(frame)
        self.assertEqual(len(bars), 4)
        self.assertTrue(all(b == 0.05 for b in bars))

    def test_low_and_high_amplitude_inputs(self) -> None:
        """Verify low-amplitude input produces smaller bar values than high-amplitude input."""
        analyzer_low = AudioAnalyzer(bar_count=5, attack_factor=1.0, min_baseline=0.0)
        analyzer_high = AudioAnalyzer(bar_count=5, attack_factor=1.0, min_baseline=0.0)

        # Low amplitude 0.1 sine wave
        low_samples = [0.1 * math.sin(2 * math.pi * 440 * i / 44100) for i in range(441)]
        low_frame = AudioFrame(samples=low_samples, sample_rate=44100, channels=1, frame_count=441)
        bars_low = analyzer_low.process_frame(low_frame)

        # High amplitude 0.9 sine wave
        high_samples = [0.9 * math.sin(2 * math.pi * 440 * i / 44100) for i in range(441)]
        high_frame = AudioFrame(samples=high_samples, sample_rate=44100, channels=1, frame_count=441)
        bars_high = analyzer_high.process_frame(high_frame)

        for b_low, b_high in zip(bars_low, bars_high):
            self.assertGreater(b_high, b_low)

    def test_synthetic_transient_attack_response(self) -> None:
        """Verify fast attack response when a high-energy transient arrives."""
        analyzer = AudioAnalyzer(bar_count=5, attack_factor=0.7, min_baseline=0.05)
        initial_bars = analyzer.current_bars
        self.assertTrue(all(b == 0.05 for b in initial_bars))

        high_samples = [0.8] * 500
        frame = AudioFrame(samples=high_samples, sample_rate=48000, channels=1, frame_count=500)
        updated_bars = analyzer.process_frame(frame)

        # Output bars should immediately rise significantly above baseline
        for b in updated_bars:
            self.assertGreater(b, 0.4)

    def test_decay_behavior(self) -> None:
        """Verify smooth decay behavior when audio transitions from loud to silent."""
        analyzer = AudioAnalyzer(bar_count=5, attack_factor=1.0, decay_factor=0.2, min_baseline=0.05)
        loud_frame = AudioFrame(samples=[0.9] * 500, sample_rate=48000, channels=1, frame_count=500)

        # Process loud frame first
        bars1 = analyzer.process_frame(loud_frame)
        self.assertTrue(all(b > 0.8 for b in bars1))

        # Process silent frame next
        silent_frame = AudioFrame(samples=[0.0] * 500, sample_rate=48000, channels=1, frame_count=500)
        bars2 = analyzer.process_frame(silent_frame)

        # Bars should decay smoothly (smaller than bars1, but still above baseline)
        for b1, b2 in zip(bars1, bars2):
            self.assertLess(b2, b1)
            self.assertGreater(b2, 0.05)

        # Process multiple silent frames -> should reach min_baseline
        for _ in range(20):
            bars_final = analyzer.process_frame(silent_frame)

        for b in bars_final:
            self.assertAlmostEqual(b, 0.05, delta=0.01)

    def test_normalization_and_clamping(self) -> None:
        """Verify bar heights are strictly clamped within range [0.0, 1.0] even with extreme input/sensitivity."""
        analyzer = AudioAnalyzer(bar_count=5, sensitivity=100.0, min_baseline=0.0)

        # Over-saturated input
        extreme_samples = [5.0, -10.0, 100.0, -50.0] * 100
        frame = AudioFrame(samples=extreme_samples, sample_rate=48000, channels=2, frame_count=200)

        bars = analyzer.process_frame(frame)
        self.assertEqual(len(bars), 5)
        for b in bars:
            self.assertGreaterEqual(b, 0.0)
            self.assertLessEqual(b, 1.0)

    def test_configurable_bar_count(self) -> None:
        """Verify analyzer handles various bar counts (e.g., 3, 5, 10, 16)."""
        for count in (1, 3, 5, 10, 16):
            analyzer = AudioAnalyzer(bar_count=count)
            frame = AudioFrame(samples=[0.5] * 200, sample_rate=44100, channels=2, frame_count=100)
            bars = analyzer.process_frame(frame)
            self.assertEqual(len(bars), count)

    def test_malformed_and_empty_input_handling(self) -> None:
        """Verify analyzer handles None, empty samples, zero channels, or invalid frames gracefully without crashing."""
        analyzer = AudioAnalyzer(bar_count=5, min_baseline=0.05)

        # None input
        bars1 = analyzer.process_frame(None)
        self.assertEqual(len(bars1), 5)

        # Empty samples
        empty_frame = AudioFrame(samples=[], sample_rate=44100, channels=2, frame_count=0)
        bars2 = analyzer.process_frame(empty_frame)
        self.assertEqual(len(bars2), 5)

        # Zero channels
        zero_ch_frame = AudioFrame(samples=[0.5, 0.5], sample_rate=44100, channels=0, frame_count=1)
        bars3 = analyzer.process_frame(zero_ch_frame)
        self.assertEqual(len(bars3), 5)

        # Negative frame count
        neg_frame = AudioFrame(samples=[0.5], sample_rate=44100, channels=1, frame_count=-5)
        bars4 = analyzer.process_frame(neg_frame)
        self.assertEqual(len(bars4), 5)

    def test_channel_handling_mono_stereo_multichannel(self) -> None:
        """Verify downmixing mono, stereo, and 5.1 multichannel audio."""
        analyzer = AudioAnalyzer(bar_count=3, attack_factor=1.0)

        # Mono (1 channel)
        mono_frame = AudioFrame(samples=[0.5] * 300, sample_rate=48000, channels=1, frame_count=300)
        bars_mono = analyzer.process_frame(mono_frame)
        self.assertEqual(len(bars_mono), 3)

        # Stereo (2 channels)
        stereo_frame = AudioFrame(samples=[0.5, -0.5] * 300, sample_rate=48000, channels=2, frame_count=300)
        bars_stereo = analyzer.process_frame(stereo_frame)
        self.assertEqual(len(bars_stereo), 3)

        # 5.1 Surround (6 channels)
        surround_frame = AudioFrame(samples=[0.2] * 1800, sample_rate=48000, channels=6, frame_count=300)
        bars_surround = analyzer.process_frame(surround_frame)
        self.assertEqual(len(bars_surround), 3)

    def test_sample_rate_metadata_handling(self) -> None:
        """Verify different sample rates (44.1kHz, 48kHz, 96kHz) do not cause errors."""
        analyzer = AudioAnalyzer(bar_count=5)
        for rate in (22050, 44100, 48000, 88200, 96000, 192000):
            frame = AudioFrame(samples=[0.3] * 400, sample_rate=rate, channels=2, frame_count=200)
            bars = analyzer.process_frame(frame)
            self.assertEqual(len(bars), 5)

    def test_deterministic_output(self) -> None:
        """Verify identical inputs produce identical bar heights."""
        analyzer1 = AudioAnalyzer(bar_count=5, attack_factor=0.6, decay_factor=0.15)
        analyzer2 = AudioAnalyzer(bar_count=5, attack_factor=0.6, decay_factor=0.15)

        samples = [math.sin(i * 0.1) * 0.5 for i in range(1000)]
        frame1 = AudioFrame(samples=samples, sample_rate=48000, channels=2, frame_count=500)
        frame2 = AudioFrame(samples=samples, sample_rate=48000, channels=2, frame_count=500)

        res1 = analyzer1.process_frame(frame1)
        res2 = analyzer2.process_frame(frame2)

        self.assertEqual(res1, res2)

    def test_cpu_safety_and_reset(self) -> None:
        """Verify reset method restores baseline and repeated execution stays bounded."""
        analyzer = AudioAnalyzer(bar_count=5, attack_factor=1.0, min_baseline=0.05)
        frame = AudioFrame(samples=[0.9] * 500, sample_rate=48000, channels=1, frame_count=500)

        bars_active = analyzer.process_frame(frame)
        self.assertTrue(all(b > 0.8 for b in bars_active))

        analyzer.reset()
        bars_reset = analyzer.current_bars
        self.assertTrue(all(b == 0.05 for b in bars_reset))


if __name__ == "__main__":
    unittest.main()
