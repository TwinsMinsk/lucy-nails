"""Voice a reel with a text-to-speech model on OpenRouter.

    python ads/audio/tts.py r08                                                 -> ads/vo/r08-tts.wav
    python ads/audio/tts.py r08 --samples                                       -> ads/vo/samples/r08/*.mp3
    python ads/audio/tts.py r08 --samples --check                               -> plus a Whisper read-back

The text is the reel's voice-over from scripts.md. The campaign voice is Gemini 3.8 Flash TTS «Sulafat»,
picked on 31.10.2026 from the R8 samples. A synthesized take has no fumbles to cut, so it goes on with
`prep_vo.py <reel> ads/vo/<reel>-tts.wav --tts`. The key is OPENROUTER_API_KEY from the environment
or, on Windows, from the user's saved variables, so a key saved with SetEnvironmentVariable works at once.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from script import ADS, normalize, vo_lines, words

API = "https://openrouter.ai/api/v1/audio/speech"
VO = ADS / "vo"

# Delivery direction for models that take one (Gemini, OpenAI); the others ignore it.
STYLE = ("Native Russian female voice of a nail artist and course author talking to fellow nail masters: "
         "warm, confident and conversational, like a friend sharing know-how, not an announcer. "
         "Lively short-video pace, clear diction, natural Russian stress.")

SAMPLES = [
    ("elevenlabs/eleven-v4", "matilda"),
    ("elevenlabs/eleven-v4", "sarah"),
    ("elevenlabs/eleven-v4", "jessica"),
    ("google/gemini-3.8-flash-tts", "Sulafat"),
    ("google/gemini-3.8-flash-tts", "Kore"),
    ("google/gemini-3.8-flash-tts", "Despina"),
    ("microsoft/mai-voice-2.1", "ru-RU-Masha:MAI-Voice-2.1"),
    ("microsoft/mai-voice-2.1", "ru-RU-Harper:MAI-Voice-2.1"),
]


def api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key and sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as env:
                key = winreg.QueryValueEx(env, "OPENROUTER_API_KEY")[0]
        except OSError:
            pass
    if not key:
        sys.exit("Set OPENROUTER_API_KEY")
    return key


def speak(text: str, model: str, voice: str, key: str, style: str | None = STYLE) -> tuple[bytes, str]:
    # Gemini and HeyGen refuse anything but raw PCM.
    fmt = "pcm" if model.startswith(("google/", "heygen/")) else "mp3"
    body = {"model": model, "input": text, "voice": voice, "response_format": fmt}
    if style:
        body["instructions"] = style
    request = urllib.request.Request(API, data=json.dumps(body, ensure_ascii=False).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.read(), response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{model} {voice}: HTTP {exc.code} {exc.read().decode(errors='replace')[:300]}") from None


def save(audio: bytes, content_type: str, dest: Path) -> Path:
    """Write the reply as `dest` (.mp3 or .wav), decoding raw PCM as 16-bit mono."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if "pcm" in content_type or "l16" in content_type.lower():
        rate = re.search(r"rate=(\d+)", content_type)
        source = ["-f", "s16le", "-ar", rate.group(1) if rate else "24000", "-ac", "1", "-i", "pipe:0"]
    else:
        source = ["-i", "pipe:0"]
    encode = ["-c:a", "libmp3lame", "-q:a", "2"] if dest.suffix == ".mp3" else ["-ar", "48000", "-ac", "1"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *source, *encode, str(dest)], input=audio, check=True)
    return dest


def seconds(path: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(path)], check=True, capture_output=True, text=True).stdout)


def read_back(paths: list[Path], text: str) -> None:
    """Whisper each take and list the script words it heard differently (misread, skipped or added)."""
    from prep_vo import transcribe

    script = [normalize(w) for w in words(text)]
    for path in paths:
        heard = [normalize(h["text"]) for h in transcribe(path, "Nail Design PRO.")]
        diffs = []
        for op, a1, a2, b1, b2 in difflib.SequenceMatcher(a=script, b=heard, autojunk=False).get_opcodes():
            # Whisper writes numbers as digits: "одиннадцать" -> "11" is not a misreading.
            if op != "equal" and not (op == "replace" and all(w.isdigit() for w in heard[b1:b2])):
                diffs.append(f"{' '.join(script[a1:a2]) or '∅'} → {' '.join(heard[b1:b2]) or '∅'}")
        ratio = difflib.SequenceMatcher(a=script, b=heard, autojunk=False).ratio()
        print(f"{path.name}: {ratio:.0%} match" + (f"; {'; '.join(diffs)}" if diffs else ""))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("reel")
    ap.add_argument("--model", default="google/gemini-3.8-flash-tts")
    ap.add_argument("--voice", default="Sulafat")
    ap.add_argument("--style", default=STYLE, help="delivery direction; empty to send none")
    ap.add_argument("--samples", action="store_true", help="voice the reel with every voice in SAMPLES")
    ap.add_argument("--check", action="store_true", help="read the takes back with Whisper")
    args = ap.parse_args()

    key = api_key()
    text = " ".join(vo_lines(args.reel))
    takes = []
    if args.samples:
        out = VO / "samples" / args.reel
        for index, (model, voice) in enumerate(SAMPLES, start=1):
            name = f"{index:02d}-{model.split('/')[1]}-{voice.split(':')[0]}.mp3"
            try:
                take = save(*speak(text, model, voice, key, args.style or None), out / name)
            except RuntimeError as err:
                print(err)
                continue
            print(f"{take.relative_to(ADS.parent)}: {seconds(take):.1f}s")
            takes.append(take)
    else:
        take = save(*speak(text, args.model, args.voice, key, args.style or None), VO / f"{args.reel}-tts.wav")
        print(f"{take.relative_to(ADS.parent)}: {seconds(take):.1f}s ({args.model}, {args.voice})")
        takes.append(take)
    if args.check and takes:
        read_back(takes, text)


if __name__ == "__main__":
    main()
