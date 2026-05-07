"""Извлечение аудио и транскрипция faster-whisper (кеш в transcript.json)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def run_ffmpeg_extract_wav(video_path: Path, wav_path: Path) -> None:
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(wav_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def transcribe_video(
    video_path: Path,
    out_dir: Path,
    *,
    model_size: str = "large-v3",
    device: str = "auto",
    compute_type: str = "default",
) -> dict[str, Any]:
    """
    Возвращает dict: duration_seconds, segments: [{start, end, text}, ...].
    Кеширует результат в out_dir / transcript.json
    """
    cache = out_dir / "transcript.json"
    if cache.is_file():
        return json.loads(cache.read_text(encoding="utf-8"))

    from faster_whisper import WhisperModel

    wav = out_dir / "audio_16k.wav"
    run_ffmpeg_extract_wav(video_path, wav)

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments_iter, info = model.transcribe(
        str(wav),
        language="ru",
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    segments: list[dict[str, Any]] = []
    for seg in segments_iter:
        segments.append(
            {
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
            }
        )

    duration = float(getattr(info, "duration", None) or segments[-1]["end"] if segments else 0.0)

    payload = {
        "duration_seconds": round(duration, 3),
        "language": getattr(info, "language", "ru"),
        "segments": segments,
    }
    cache.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
