import os
import tempfile
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from pydub import AudioSegment

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
LULLABY_TEMPLATE = os.path.join(ASSETS_DIR, "lullaby_template.mp3")
HEARTBEAT_ATTENUATION_DB = -15
OUTPUT_BITRATE = "192k"
MIN_OUTPUT_DURATION_MS = 120_000  # 2 minutes minimum


def _generate_sine_placeholder(duration_s: int = 180, bpm: float = 70.0, sr: int = 44100) -> np.ndarray:
    """Fallback: generate a simple sine wave when lullaby_template.mp3 is absent."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    freq = 261.63  # middle C
    return (np.sin(2 * np.pi * freq * t) * 0.3).astype(np.float32)


def compose(cleaned_wav_path: str, baby_bpm: float, output_mp3_path: str) -> None:
    """
    Compose the final lullaby MP3.

    - Time-stretches the piano template to match baby_bpm (pitch-preserving via librosa).
    - Overlays the cleaned heartbeat at -15 dB as a rhythmic low-end layer.
    - Exports as 192k MP3.
    """
    sr = 44100

    # Load template (use sine placeholder if file not yet sourced)
    if os.path.exists(LULLABY_TEMPLATE):
        template_y, template_sr = librosa.load(LULLABY_TEMPLATE, sr=sr, mono=False)
        if template_y.ndim > 1:
            template_y = librosa.to_mono(template_y)
        template_tempo, _ = librosa.beat.beat_track(y=template_y, sr=sr)
        template_bpm = float(template_tempo)
    else:
        template_y = _generate_sine_placeholder(180, baby_bpm, sr)
        template_bpm = baby_bpm  # no stretching needed for placeholder

    # Time-stretch to match baby's BPM (pitch-preserving — do NOT use pydub speedup())
    if template_bpm > 0 and abs(template_bpm - baby_bpm) > 2:
        stretch_rate = baby_bpm / template_bpm
        template_y = librosa.effects.time_stretch(template_y, rate=stretch_rate)

    # Write stretched template to temp WAV
    stretched_wav = os.path.join(tempfile.gettempdir(), "stretched_template.wav")
    sf.write(stretched_wav, template_y, sr)

    # Load into pydub
    lullaby = AudioSegment.from_wav(stretched_wav)

    # Ensure minimum duration by looping
    while len(lullaby) < MIN_OUTPUT_DURATION_MS:
        lullaby = lullaby + lullaby

    # Load heartbeat, attenuate, and overlay in a loop
    heartbeat = AudioSegment.from_wav(cleaned_wav_path) + HEARTBEAT_ATTENUATION_DB
    if len(heartbeat) == 0:
        raise ValueError("Cleaned audio is empty — cannot compose lullaby")

    # Build a heartbeat track the same length as lullaby by repeating
    repeated = AudioSegment.empty()
    while len(repeated) < len(lullaby):
        repeated += heartbeat
    repeated = repeated[: len(lullaby)]

    output = lullaby.overlay(repeated)
    output.export(output_mp3_path, format="mp3", bitrate=OUTPUT_BITRATE)
