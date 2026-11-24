"""Time-domain audio analysis engine for real-time media visualization.

Processes PCM AudioFrame data from WASAPI capture layer and generates normalized,
smoothed visualizer bar heights in range 0.0–1.0. Zero third-party dependencies.
"""

import math
from typing import List, Optional, Sequence
from src.media.audio_capture import AudioFrame


class AudioAnalyzer:
    """Time-domain audio analysis engine converting AudioFrame PCM data to normalized bar heights."""

    def __init__(
        self,
        bar_count: int = 5,
        attack_factor: float = 0.6,
        decay_factor: float = 0.15,
        min_baseline: float = 0.05,
        sensitivity: float = 1.0,
    ) -> None:
        """Initialize AudioAnalyzer with configuration parameters.

        Args:
            bar_count: Number of output energy bars/sub-windows (default 5, min 1).
            attack_factor: Smoothing factor when energy increases (0.0 to 1.0, default 0.6).
            decay_factor: Smoothing factor when energy decreases (0.0 to 1.0, default 0.15).
            min_baseline: Baseline height during silence (0.0 to 1.0, default 0.05).
            sensitivity: Gain multiplier for input energy (default 1.0).
        """
        self._bar_count = max(1, int(bar_count))
        self._attack_factor = max(0.0, min(1.0, float(attack_factor)))
        self._decay_factor = max(0.0, min(1.0, float(decay_factor)))
        self._min_baseline = max(0.0, min(1.0, float(min_baseline)))
        self._sensitivity = max(0.0, float(sensitivity))

        # Audio EQ & Dynamic Enhancements
        self._preamp_multiplier: float = 1.0
        self._noise_gate_threshold: float = 0.0
        self._eq_weights: List[float] = [1.0] * self._bar_count

        # Current smoothed bar heights
        self._current_bars: List[float] = [self._min_baseline] * self._bar_count

    @property
    def bar_count(self) -> int:
        """Return configured bar count."""
        return self._bar_count

    @property
    def min_baseline(self) -> float:
        """Return configured baseline floor."""
        return self._min_baseline

    @property
    def attack_factor(self) -> float:
        """Return attack factor."""
        return self._attack_factor

    @property
    def decay_factor(self) -> float:
        """Return decay factor."""
        return self._decay_factor

    @property
    def sensitivity(self) -> float:
        """Return sensitivity multiplier."""
        return self._sensitivity

    @property
    def current_bars(self) -> List[float]:
        """Return copy of current smoothed bar heights."""
        return list(self._current_bars)

    def reset(self) -> None:
        """Reset internal smoothed bar states back to min_baseline."""
        self._current_bars = [self._min_baseline] * self._bar_count

    def set_eq_profile(
        self,
        preamp_boost_db: float = 0.0,
        bass_db: float = 0.0,
        clarity_db: float = 0.0,
        treble_db: float = 0.0,
        eq_bands: Optional[Sequence[float]] = None,
        noise_gate_percent: int = 0,
        eq_enabled: bool = True,
    ) -> None:
        """Configure dynamic audio equalizer profile and noise filter for visualizer reaction.

        Args:
            preamp_boost_db: Preamp boost in dB (0.0 to 12.0 dB).
            bass_db: Bass tone slider in dB (-12.0 to +12.0 dB).
            clarity_db: Mid/vocal clarity slider in dB (-12.0 to +12.0 dB).
            treble_db: Treble tone slider in dB (-12.0 to +12.0 dB).
            eq_bands: 5-band graphic EQ levels in dB [60Hz, 250Hz, 1kHz, 4kHz, 16kHz].
            noise_gate_percent: Noise gate threshold (0 to 50%).
            eq_enabled: Whether EQ profile is active.
        """
        if not eq_enabled:
            self._preamp_multiplier = 1.0
            self._noise_gate_threshold = 0.0
            self._eq_weights = [1.0] * self._bar_count
            return

        # 1. Preamp Multiplier
        boost = max(0.0, min(12.0, float(preamp_boost_db)))
        self._preamp_multiplier = math.pow(10.0, boost / 20.0)

        # 2. Noise Gate Threshold
        gate = max(0, min(50, int(noise_gate_percent)))
        self._noise_gate_threshold = (gate / 100.0) * 0.40

        # 3. Frequency Weights per Bar
        bands = list(eq_bands) if (eq_bands and len(eq_bands) >= 5) else [0.0] * 5
        # Compute combined dB offset for 5 sub-windows
        # Bar 0: Sub-bass / Bass (60Hz + Bass slider)
        # Bar 1: Low-mids (250Hz + 0.5 * Bass slider)
        # Bar 2: Midrange / Clarity (1kHz + Clarity slider)
        # Bar 3: High-mids (4kHz + 0.5 * Clarity slider)
        # Bar 4: Treble / Air (16kHz + Treble slider)
        db_offsets = [
            bands[0] + bass_db,
            bands[1] + 0.5 * bass_db,
            bands[2] + clarity_db,
            bands[3] + 0.5 * clarity_db,
            bands[4] + treble_db,
        ]

        self._eq_weights = []
        for i in range(self._bar_count):
            idx = min(i, len(db_offsets) - 1)
            # Convert dB to linear gain multiplier, clamped between 0.1 and 4.0
            gain = math.pow(10.0, db_offsets[idx] / 20.0)
            self._eq_weights.append(max(0.1, min(4.0, gain)))

    def process_frame(self, frame: Optional[AudioFrame]) -> List[float]:
        """Process an AudioFrame and return normalized bar heights in range [0.0, 1.0].

        Args:
            frame: Optional AudioFrame container with PCM samples and metadata.

        Returns:
            List of floats of length `bar_count`, each value clamped to [0.0, 1.0].
        """
        if (
            frame is None
            or not hasattr(frame, "samples")
            or not frame.samples
            or getattr(frame, "frame_count", 0) <= 0
            or getattr(frame, "channels", 0) <= 0
        ):
            # No valid audio data -> decay towards min_baseline
            self._apply_decay_only()
            return list(self._current_bars)

        samples = frame.samples
        channels = max(1, int(frame.channels))
        frame_count = int(frame.frame_count)
        total_samples = len(samples)

        # Validate sample array bounds
        usable_frames = min(frame_count, total_samples // channels)
        if usable_frames <= 0:
            self._apply_decay_only()
            return list(self._current_bars)

        # 1. Downmix interleaved multi-channel samples to mono
        mono_samples: List[float] = []
        if channels == 1:
            mono_samples = [float(s) for s in samples[:usable_frames]]
        else:
            for i in range(usable_frames):
                offset = i * channels
                frame_sum = sum(samples[offset + c] for c in range(channels))
                mono_samples.append(frame_sum / channels)

        # 2. Divide mono samples into `bar_count` sub-windows and calculate RMS energy per window
        raw_bar_energies = self._calculate_subwindow_rms(mono_samples)

        # 3. Apply attack / decay temporal smoothing, EQ weights, and baseline floor
        for k in range(self._bar_count):
            raw = raw_bar_energies[k]

            # Apply noise gate filter: if energy is below noise gate threshold, treat as silence
            if raw < self._noise_gate_threshold:
                target = self._min_baseline
            else:
                weight = self._eq_weights[k] if k < len(self._eq_weights) else 1.0
                target = raw * self._sensitivity * self._preamp_multiplier * weight
                target = max(0.0, min(1.0, target))

            current = self._current_bars[k]
            if target > current:
                new_val = current + (target - current) * self._attack_factor
            else:
                new_val = current + (target - current) * self._decay_factor

            # Ensure value is clamped within [min_baseline, 1.0]
            self._current_bars[k] = max(self._min_baseline, min(1.0, new_val))

        return list(self._current_bars)

    def _apply_decay_only(self) -> None:
        """Decay all bars towards min_baseline when no audio is present."""
        for k in range(self._bar_count):
            current = self._current_bars[k]
            new_val = current + (self._min_baseline - current) * self._decay_factor
            self._current_bars[k] = max(self._min_baseline, min(1.0, new_val))

    def _calculate_subwindow_rms(self, mono_samples: List[float]) -> List[float]:
        """Calculate Root Mean Square (RMS) energy for `bar_count` sub-windows."""
        n_samples = len(mono_samples)
        if n_samples == 0:
            return [0.0] * self._bar_count

        energies: List[float] = []
        chunk_size = n_samples / self._bar_count

        for k in range(self._bar_count):
            start_idx = int(k * chunk_size)
            end_idx = int((k + 1) * chunk_size) if k < self._bar_count - 1 else n_samples

            if start_idx >= end_idx:
                energies.append(0.0)
                continue

            chunk = mono_samples[start_idx:end_idx]
            sum_sq = sum(s * s for s in chunk)
            rms = math.sqrt(sum_sq / len(chunk))

            # Apply perceptual compression curve for visual responsiveness
            perceptual = math.pow(rms, 0.75) if rms > 0 else 0.0
            energies.append(min(1.0, perceptual))

        return energies
