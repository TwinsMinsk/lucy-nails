"""Clean a voice-over take and time every word of the script against it.

    python ads/audio/prep_vo.py r03 ads/vo/r03-take2.wav        # a real recording
    python ads/audio/prep_vo.py r03 ads/vo/r03-placeholder.wav --draft

Real takes: auto-editor cuts pauses and fumbles, then high-pass, light denoise and
loudness to -16 LUFS. Draft and synthesized (--tts, from tts.py) takes skip the cutting and the denoise.

Words come from faster-whisper (large-v3, word timestamps) but the text on screen is
always the script's: recognised words are matched to script words in order and only
lend their times; script words Whisper missed get times interpolated between neighbours.

Output: ads/cache/vo/<reel>.wav and ads/cache/vo/<reel>.words.json
"""

from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
from pathlib import Path

from script import ADS, normalize, vo_lines, words

REPO = ADS.parent
OUT = ADS / "cache" / "vo"
AUTO_EDITOR = ADS / ".venv" / "Scripts" / "auto-editor.exe"

# CUDA DLL registration for CTranslate2 on Windows is already solved in the subtitle pipeline.
sys.path.insert(0, str(REPO / "scripts" / "subtitles"))
from transcribe_words import _register_cuda_dlls  # noqa: E402


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def clean(reel: str, take: Path, draft: bool) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    src = take
    if not draft:
        cut = OUT / f"{reel}.cut.wav"
        subprocess.run([str(AUTO_EDITOR), str(take), "--edit", "audio:threshold=0.04", "--margin", "0.12s",
                        "--output", str(cut), "--no-open"], check=True)
        src = cut
    out = OUT / f"{reel}.wav"
    chain = "highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=7" if draft else \
        "highpass=f=80,afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=7"
    ffmpeg("-i", str(src), "-af", chain, "-ar", "48000", "-ac", "1", str(out))
    return out


def load_model(cpu: bool = False):
    """int8 on the GPU when it has room; the GPU is often shared, and a 30 s take is quick on CPU too."""
    _register_cuda_dlls()
    from faster_whisper import WhisperModel

    if not cpu:
        try:
            return WhisperModel("large-v3", device="cuda", compute_type="int8_float16")
        except (RuntimeError, ValueError) as err:
            print(f"GPU unavailable ({err}); transcribing on CPU")
    return WhisperModel("large-v3", device="cpu", compute_type="int8", cpu_threads=16)


def pcm16k(audio: Path):
    """Decode with ffmpeg: faster-whisper's own PyAV decoder breaks on the PyAV version uv resolves."""
    import numpy as np

    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(audio), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def transcribe(audio: Path, prompt: str) -> list[dict]:
    pcm = pcm16k(audio)

    def run(model) -> list[dict]:
        segments, _ = model.transcribe(pcm, language="ru", word_timestamps=True,
                                       initial_prompt=prompt, vad_filter=False, beam_size=5)
        return [{"text": w.word.strip(), "start": w.start, "end": w.end}
                for seg in segments for w in seg.words if normalize(w.word)]

    try:
        return run(load_model())
    except RuntimeError as err:  # the model fit on the GPU but decoding did not
        print(f"GPU failed while decoding ({err}); transcribing on CPU")
        return run(load_model(cpu=True))


def align(lines: list[str], heard: list[dict], total: float) -> list[dict]:
    script = [(li, w) for li, line in enumerate(lines) for w in words(line)]
    a = [normalize(w) for _, w in script]
    b = [normalize(h["text"]) for h in heard]
    times: list[tuple[float, float] | None] = [None] * len(script)
    for block in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_matching_blocks():
        for k in range(block.size):
            h = heard[block.b + k]
            times[block.a + k] = (h["start"], h["end"])
    # Interpolate words Whisper missed or heard differently.
    known = [i for i, t in enumerate(times) if t]
    for i, t in enumerate(times):
        if t:
            continue
        prev = max((k for k in known if k < i), default=None)
        nxt = min((k for k in known if k > i), default=None)
        start = times[prev][1] if prev is not None else 0.0
        end = times[nxt][0] if nxt is not None else total
        span_from = prev if prev is not None else -1
        span_to = nxt if nxt is not None else len(script)
        n = span_to - span_from - 1
        step = (end - start) / max(n, 1)
        k = i - span_from - 1
        times[i] = (start + k * step, start + (k + 1) * step)
    matched = len(known) / max(len(script), 1)

    out = []
    for li, line in enumerate(lines):
        ws = [{"text": w, "start": round(times[i][0], 3), "end": round(times[i][1], 3)}
              for i, (l, w) in enumerate(script) if l == li]
        out.append({"text": line, "start": ws[0]["start"], "end": ws[-1]["end"], "words": ws})
    print(f"matched {matched:.0%} of script words to the recording")
    return out


def duration(path: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(path)], check=True, capture_output=True, text=True).stdout)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("reel")
    ap.add_argument("take", type=Path)
    ap.add_argument("--draft", action="store_true", help="placeholder TTS take: no pause cutting")
    ap.add_argument("--tts", action="store_true", help="final synthesized take (ads/audio/tts.py): no pause cutting")
    args = ap.parse_args()

    lines = vo_lines(args.reel)
    audio = clean(args.reel, args.take, args.draft or args.tts)
    total = duration(audio)
    # Only the course name as a prompt: with the whole script as the prompt Whisper skipped most of the R2 draft.
    heard = transcribe(audio, "Nail Design PRO.")
    timed = align(lines, heard, total)
    data = {"reel": args.reel, "audio": str(audio.relative_to(ADS)).replace("\\", "/"),
            "draft": args.draft, "duration": round(total, 3), "lines": timed}
    path = OUT / f"{args.reel}.words.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{path}: {len(timed)} lines, {total:.1f}s")


if __name__ == "__main__":
    main()
