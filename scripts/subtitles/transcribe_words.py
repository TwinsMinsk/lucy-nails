"""
Распознавание со словными таймкодами (faster-whisper large-v3).

Отличия от scripts/promo/transcribe.py, который делал старые субтитры:
  * word_timestamps=True — без времени по словам нельзя ни резать по смыслу,
    ни возвращать тайминги после правки текста;
  * защита от петель без потери пунктуации. Старый транскрипт содержит дословные
    повторы (сегменты 76.83-85.53 и 85.69-87.61 совпадают) — это петля Whisper на
    подсказке собственным предыдущим текстом. Отключать подсказку нельзя: в
    faster-whisper initial_prompt живёт только в первом окне, дальше модель
    остаётся без контекста и перестаёт ставить знаки препинания, а на них держится
    вся разбивка на строки. Поэтому контекст сохраняем, а петли давим штрафом за
    повторы, сбросом подсказки при росте температуры и порогом на тишину;
  * initial_prompt с терминологией курса — поднимает точность на профлексике.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from paths import promo_output_dir


def _register_cuda_dlls() -> None:
    """CTranslate2 на Windows ищет cuBLAS и cuDNN в PATH; ставим их из колёс nvidia-*."""
    if sys.platform != "win32":
        return
    try:
        import nvidia
    except ImportError:
        return
    # nvidia — namespace-пакет, у него __file__ = None, поэтому идём через __path__
    roots = [Path(p) for p in getattr(nvidia, "__path__", [])]
    for base in roots:
        for sub in ("cublas/bin", "cudnn/bin", "cuda_runtime/bin"):
            path = base / sub
            if path.is_dir():
                os.add_dll_directory(str(path))
                os.environ["PATH"] = f"{path}{os.pathsep}{os.environ.get('PATH', '')}"


def extract_audio(video: Path, wav: Path) -> Path:
    """16 кГц моно. Если промо-пайплайн уже извлёк аудио — переиспользуем."""
    if wav.is_file() and wav.stat().st_size > 0:
        return wav
    wav.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
         "-c:a", "pcm_s16le", str(wav)],
        check=True, capture_output=True,
    )
    return wav


def find_audio(slug: str, video: Path, work_dir: Path) -> Path:
    shared = promo_output_dir(slug) / "audio_16k.wav"
    if shared.is_file() and shared.stat().st_size > 0:
        return shared
    return extract_audio(video, work_dir / "audio_16k.wav")


def load_model(model_size: str = "large-v3") -> tuple[Any, str]:
    from faster_whisper import WhisperModel

    _register_cuda_dlls()
    try:
        model = WhisperModel(model_size, device="cuda", compute_type="float16")
        return model, "cuda/float16"
    except Exception as exc:  # нет CUDA-библиотек или мало памяти
        print(f"  GPU недоступен ({type(exc).__name__}), переключаюсь на CPU", flush=True)
        return WhisperModel(model_size, device="cpu", compute_type="int8"), "cpu/int8"


def transcribe(
    audio: Path,
    out_json: Path,
    *,
    initial_prompt: str = "",
    model_size: str = "large-v3",
    force: bool = False,
) -> dict[str, Any]:
    if out_json.is_file() and not force:
        return json.loads(out_json.read_text(encoding="utf-8"))

    model, backend = load_model(model_size)
    print(f"  распознавание {audio.name} на {backend}", flush=True)

    segments_iter, info = model.transcribe(
        str(audio),
        language="ru",
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 350, "speech_pad_ms": 200},
        condition_on_previous_text=True,
        prompt_reset_on_temperature=0.5,
        repetition_penalty=1.15,
        hallucination_silence_threshold=2.0,
        compression_ratio_threshold=2.4,
        no_speech_threshold=0.6,
        temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        beam_size=5,
        initial_prompt=initial_prompt or None,
    )

    words: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []
    for seg in segments_iter:
        segments.append({"start": round(seg.start, 3), "end": round(seg.end, 3),
                         "text": seg.text.strip()})
        for w in (seg.words or []):
            text = w.word.strip()
            if not text:
                continue
            words.append({
                "w": text,
                "start": round(w.start, 3),
                "end": round(w.end, 3),
                "prob": round(float(getattr(w, "probability", 1.0)), 3),
            })
        if len(segments) % 25 == 0:
            print(f"    …{seg.end:.0f} с, слов {len(words)}", flush=True)

    payload = {
        "duration_seconds": round(float(getattr(info, "duration", 0.0)), 3),
        "language": getattr(info, "language", "ru"),
        "backend": backend,
        "model": model_size,
        "words": words,
        "segments": segments,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return payload


if __name__ == "__main__":
    import argparse

    from correct_text import load_glossary
    from paths import lesson_dirs, resolve_lesson

    ap = argparse.ArgumentParser(description="Распознать урок со словными таймкодами")
    ap.add_argument("--lesson", required=True)
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    video, title = resolve_lesson(args.lesson)
    dirs = lesson_dirs(args.lesson)
    dirs["work"].mkdir(parents=True, exist_ok=True)
    dirs["subs"].mkdir(parents=True, exist_ok=True)

    audio = find_audio(args.lesson, video, dirs["work"])
    result = transcribe(
        audio,
        dirs["subs"] / f"{args.lesson}.words.json",
        initial_prompt=load_glossary().get("prompt_terms", ""),
        model_size=args.model,
        force=args.force,
    )
    print(f"{title}: слов {len(result['words'])}, сегментов {len(result['segments'])}, "
          f"{result['duration_seconds']:.0f} с")
