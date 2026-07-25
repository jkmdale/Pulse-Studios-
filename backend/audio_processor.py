import os
import tempfile
from pathlib import Path

import ffmpeg
import librosa
import numpy as np
import soundfile as sf


SUPPORTED_EXTENSIONS = {".mov", ".mp4", ".m4a", ".mp3", ".wav", ".3gp", ".aac"}
PEAKS_COUNT = 500


def extract_audio_from_video(input_path: str, output_wav_path: str) -> None:
    """
    Extract audio from any supported format and apply heartbeat-isolation filters.

    Filter chain:
    - highpass f=80  — removes low-frequency handling noise and rumble
    - lowpass f=600  — removes high-frequency Doppler carrier artifact
    (These are Hz values, not BPM — the bandpass targets fetal heartbeat audio energy.)
    """
    ext = Path(input_path).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported input format: {ext}")

    try:
        stream = ffmpeg.input(input_path)
        audio = stream.audio
        filtered = audio.filter("highpass", f=80).filter("lowpass", f=600)
        out = ffmpeg.output(filtered, output_wav_path, ar=44100, ac=1, acodec="pcm_s16le")
        ffmpeg.run(out, overwrite_output=True, quiet=True)
    except ffmpeg.Error as e:
        raise RuntimeError(f"FFmpeg processing failed: {e.stderr.decode() if e.stderr else e}") from e


def detect_bpm(y: np.ndarray, sr: int) -> float:
    """
    Detect fetal heartbeat BPM using librosa beat tracking.

    Applies conditional doubling: librosa may detect one sound per cycle (needs 2x)
    or both lub+dub separately (already correct range). Clamps to physiological range.
    """
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(tempo)
    if bpm < 100:
        bpm *= 2
    return max(100.0, min(220.0, bpm))


def extract_peaks(y: np.ndarray) -> list:
    """Extract ~500 normalized RMS amplitude points for waveform art."""
    hop = max(1, len(y) // PEAKS_COUNT)
    rms = librosa.feature.rms(y=y, frame_length=512, hop_length=hop)
    values = rms[0].tolist()
    peak_max = max(values) if values else 1.0
    if peak_max == 0:
        peak_max = 1.0
    return [v / peak_max for v in values[:PEAKS_COUNT]]


def process_audio(input_path: str, order_id: str) -> dict:
    """
    Full audio processing pipeline.

    Returns:
        {
            "bpm": float,
            "peaks": list[float],  # ~500 normalized values 0.0-1.0
            "cleaned_wav_path": str,
        }
    """
    cleaned_wav_path = os.path.join(tempfile.gettempdir(), f"{order_id}_cleaned.wav")
    extract_audio_from_video(input_path, cleaned_wav_path)

    y, sr = librosa.load(cleaned_wav_path, sr=None, mono=True)
    if len(y) == 0:
        raise ValueError("Audio file is empty after filtering — check input format")

    bpm = detect_bpm(y, sr)
    peaks = extract_peaks(y)

    return {
        "bpm": round(bpm, 2),
        "peaks": peaks,
        "cleaned_wav_path": cleaned_wav_path,
    }
