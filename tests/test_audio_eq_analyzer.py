"""Unit tests verifying AudioAnalyzer reactive visualizer modifications under EQ, Preamp, and Noise Gate."""

import unittest
from src.media.audio_capture import AudioFrame
from src.media.audio_analyzer import AudioAnalyzer


class TestAudioEQAnalyzer(unittest.TestCase):
    """Test suite ensuring EQ profiles, preamp boost, and noise gates alter bar output heights."""

    def setUp(self) -> None:
        self.analyzer = AudioAnalyzer(bar_count=5, attack_factor=1.0, decay_factor=1.0, min_baseline=0.05)

    def _create_frame(self, amplitude: float = 0.5, frame_count: int = 100) -> AudioFrame:
        """Create a mono PCM float audio frame with constant amplitude."""
        samples = [amplitude] * frame_count
        return AudioFrame(samples=samples, channels=1, sample_rate=48000, frame_count=frame_count)

    def test_preamp_boost_increases_visualizer_bars(self) -> None:
        """Verify audio boost (preamp) increases output bar heights proportionally."""
        frame = self._create_frame(amplitude=0.2)

        # Baseline with flat EQ
        self.analyzer.set_eq_profile(preamp_boost_db=0.0, eq_enabled=True)
        baseline_bars = self.analyzer.process_frame(frame)

        # +6 dB boost (~2.0x gain multiplier)
        self.analyzer.set_eq_profile(preamp_boost_db=6.0, eq_enabled=True)
        boosted_bars = self.analyzer.process_frame(frame)

        for b, base in zip(boosted_bars, baseline_bars):
            self.assertGreater(b, base, "Boosted bar should be higher than baseline bar")

    def test_bass_boost_increases_bass_bar_specifically(self) -> None:
        """Verify bass boost specifically boosts the leftmost bar (bar 0) more than higher frequencies."""
        frame = self._create_frame(amplitude=0.2)

        # Flat EQ
        self.analyzer.set_eq_profile(bass_db=0.0, eq_enabled=True)
        flat_bars = self.analyzer.process_frame(frame)

        # +8 dB bass boost
        self.analyzer.set_eq_profile(bass_db=8.0, eq_enabled=True)
        bass_boosted_bars = self.analyzer.process_frame(frame)

        # Bar 0 (Bass sub-window) should show greatest gain increase
        gain_bar0 = bass_boosted_bars[0] / flat_bars[0]
        gain_bar4 = bass_boosted_bars[4] / flat_bars[4]
        self.assertGreater(gain_bar0, gain_bar4, "Bass boost should amplify bar 0 more than bar 4")

    def test_noise_gate_suppresses_low_amplitude_noise(self) -> None:
        """Verify noise gate suppresses low-amplitude noise below threshold down to baseline."""
        # Low noise frame (amplitude 0.08, which is above min_baseline 0.05)
        noise_frame = self._create_frame(amplitude=0.08)

        # Without noise gate
        self.analyzer.set_eq_profile(noise_gate_percent=0, eq_enabled=True)
        ungated_bars = self.analyzer.process_frame(noise_frame)
        self.assertGreater(ungated_bars[0], 0.05)

        # With 40% noise gate (threshold ~0.08)
        self.analyzer.set_eq_profile(noise_gate_percent=50, eq_enabled=True)
        gated_bars = self.analyzer.process_frame(noise_frame)
        for b in gated_bars:
            self.assertEqual(b, 0.05, "Low noise frame should be clamped to min_baseline under noise gate")

    def test_bypassing_eq_restores_standard_levels(self) -> None:
        """Verify setting eq_enabled=False bypasses boost and EQ weights."""
        frame = self._create_frame(amplitude=0.3)

        self.analyzer.set_eq_profile(preamp_boost_db=10.0, bass_db=8.0, eq_enabled=False)
        bars = self.analyzer.process_frame(frame)

        # Default flat with eq_enabled=True
        self.analyzer.set_eq_profile(preamp_boost_db=0.0, bass_db=0.0, eq_enabled=True)
        flat_bars = self.analyzer.process_frame(frame)

        for b, flat in zip(bars, flat_bars):
            self.assertAlmostEqual(b, flat, places=3, msg="Bypassed EQ should match 0 dB flat levels")


if __name__ == "__main__":
    unittest.main()
