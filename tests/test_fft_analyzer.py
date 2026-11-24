"""Unit tests for AudioAnalyzer Fast Fourier Transform (FFT) analysis."""

import unittest
import math
from src.media.audio_capture import AudioFrame
from src.media.audio_analyzer import AudioAnalyzer


class TestFFTAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = AudioAnalyzer(bar_count=5, mode="fft")

    def test_mode_property_and_switching(self):
        self.assertEqual(self.analyzer.mode, "fft")
        self.analyzer.set_mode("rms")
        self.assertEqual(self.analyzer.mode, "rms")
        self.analyzer.set_mode("fft")
        self.assertEqual(self.analyzer.mode, "fft")

    def test_radix2_fft_impulse(self):
        # FFT of unit impulse [1, 0, 0, 0] is all 1s
        impulse = [complex(1.0, 0.0), complex(0.0, 0.0), complex(0.0, 0.0), complex(0.0, 0.0)]
        res = AudioAnalyzer._fft_radix2(impulse)
        for val in res:
            self.assertAlmostEqual(abs(val), 1.0, places=4)

    def test_fft_spectrum_calculation_with_sine_wave(self):
        # 48000 Hz sample rate, 256 samples of 1000 Hz sine wave
        sr = 48000
        samples = [math.sin(2.0 * math.pi * 1000.0 * i / sr) for i in range(256)]
        frame = AudioFrame(samples=samples, channels=1, frame_count=256, sample_rate=sr)

        bars = self.analyzer.process_frame(frame)
        self.assertEqual(len(bars), 5)
        # Mid-range bar (around 1kHz) should be elevated above silence floor
        self.assertTrue(max(bars) > self.analyzer.min_baseline)


if __name__ == "__main__":
    unittest.main()
