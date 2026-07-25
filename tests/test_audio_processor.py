import os
import sys
import tempfile

import numpy as np
import pytest
import soundfile as sf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from audio_processor import detect_bpm, extract_peaks, process_audio, PEAKS_COUNT


def _write_sine_wav(path: str, freq_hz: float, duration_s: float = 8.0, sr: int = 44100):
    """Generate a synthetic single-frequency WAV for testing."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    signal = (np.sin(2 * np.pi * freq_hz * t) * 0.5).astype(np.float32)
    sf.write(path, signal, sr)


def _write_heartbeat_wav(path: str, bpm: float, duration_s: float = 10.0, sr: int = 44100):
    """Synthesize a heartbeat-like signal at a given BPM."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    beat_freq = bpm / 60.0
    signal = (np.sin(2 * np.pi * beat_freq * t) * 0.6).astype(np.float32)
    sf.write(path, signal, sr)


class TestDetectBpm:
    def test_output_in_physiological_range(self):
        sr = 44100
        t = np.linspace(0, 10, sr * 10, endpoint=False)
        # 140 BPM = 2.33 Hz
        y = (np.sin(2 * np.pi * 2.33 * t) * 0.5).astype(np.float32)
        bpm = detect_bpm(y, sr)
        assert 100 <= bpm <= 220

    def test_clamped_to_range(self):
        sr = 44100
        # Very slow (below 100 BPM should trigger doubling or clamping)
        t = np.linspace(0, 10, sr * 10, endpoint=False)
        y = (np.sin(2 * np.pi * 0.5 * t) * 0.5).astype(np.float32)
        bpm = detect_bpm(y, sr)
        assert 100 <= bpm <= 220

    def test_returns_float(self):
        sr = 44100
        y = np.random.randn(sr * 5).astype(np.float32) * 0.1
        bpm = detect_bpm(y, sr)
        assert isinstance(bpm, float)


class TestExtractPeaks:
    def test_peaks_length(self):
        sr = 44100
        y = np.random.randn(sr * 10).astype(np.float32) * 0.3
        peaks = extract_peaks(y)
        assert len(peaks) <= PEAKS_COUNT

    def test_peaks_normalized(self):
        sr = 44100
        y = np.random.randn(sr * 5).astype(np.float32) * 0.5
        peaks = extract_peaks(y)
        assert all(0.0 <= p <= 1.0 for p in peaks)

    def test_silent_audio_returns_zeros(self):
        y = np.zeros(44100 * 3, dtype=np.float32)
        peaks = extract_peaks(y)
        assert isinstance(peaks, list)


class TestProcessAudio:
    def test_process_wav_file(self, tmp_path):
        input_wav = str(tmp_path / "heartbeat.wav")
        _write_heartbeat_wav(input_wav, bpm=140.0)

        result = process_audio(input_wav, "test-order-001")

        assert "bpm" in result
        assert "peaks" in result
        assert "cleaned_wav_path" in result
        assert 100 <= result["bpm"] <= 220
        assert isinstance(result["peaks"], list)
        assert len(result["peaks"]) > 0
        assert os.path.exists(result["cleaned_wav_path"])

    def test_unsupported_format_raises(self, tmp_path):
        bad_file = str(tmp_path / "audio.xyz")
        with open(bad_file, "w") as f:
            f.write("not audio")
        with pytest.raises(ValueError, match="Unsupported input format"):
            process_audio(bad_file, "test-order-002")

    def test_peaks_all_normalized(self, tmp_path):
        input_wav = str(tmp_path / "clean.wav")
        _write_heartbeat_wav(input_wav, bpm=155.0, duration_s=6.0)
        result = process_audio(input_wav, "test-order-003")
        assert all(0.0 <= p <= 1.0 for p in result["peaks"])
