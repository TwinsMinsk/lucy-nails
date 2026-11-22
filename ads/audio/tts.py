"""Voice a reel with text-to-speech: Lucy's cloned voice on ElevenLabs, or a stock voice on OpenRouter.

    python ads/audio/tts.py r08 --check                                         -> ads/vo/r08-tts.wav
    python ads/audio/tts.py r08 --stress                                        -> words missing a stress entry
    python ads/audio/tts.py r08 --engine openrouter                             -> stock «Sulafat» instead
    python ads/audio/tts.py r08 --samples --check                               -> ads/vo/samples/r08/*.mp3

The text is the reel's voice-over from scripts.md. The campaign voice is Lucy's instant clone on Eleven v4
(chosen 22.11.2026; the clone was made from six clean 30 s clips of the lessons). Before synthesis every word
gets its stress from stress-ru.tsv, which v4 obeys; a reel with words missing from it stops until they are
added. A synthesized take has no fumbles to cut, so it goes on with `prep_vo.py <reel> ads/vo/<reel>-tts.wav
--tts`. Keys: ELEVENLABS_API_KEY and OPENROUTER_API_KEY, from the environment, the user's saved Windows
variables or the repo's .env (never committed).
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
from stress import mark, missing

API = "https://openrouter.ai/api/v1/audio/speech"
VO = ADS / "vo"

ELEVEN_API = "https://api.elevenlabs.io/v1"
LUCY_VOICE = "d5AI9GyPZND5KKMC609O"  # «Lucy (probe 2)» in the campaign's ElevenLabs account
LUCY_MODEL = "eleven_v4"
LUCY_SETTINGS = {"stability": 0.5, "similarity_boost": 1.0}

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


def env_files() -> list[Path]:
    """The repo's .env, then the main checkout's one when running from a git worktree."""
    found = [ADS.parent / ".env"]
    try:
        common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=ADS,
                                capture_output=True, text=True, check=True).stdout.strip()
        found.append(Path(common).parent / ".env")
    except (OSError, subprocess.CalledProcessError):
        pass
    return [p for p in dict.fromkeys(found) if p.exists()]


def api_key(name: str = "OPENROUTER_API_KEY") -> str:
    key = os.environ.get(name, "")
    if not key and sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as env:
                key = winreg.QueryValueEx(env, name)[0]
        except OSError:
            pass
    for dotenv in env_files():
        if key:
            break
        for line in dotenv.read_text(encoding="utf-8-sig").splitlines():
            var, sep, value = line.partition("=")
            if sep and var.strip() == name:
                key = value.strip().strip("'\"")
    if not key:
        sys.exit(f"Set {name}")
    return key


def speak_lucy(text: str, key: str) -> tuple[bytes, str]:
    """Lucy's cloned voice on ElevenLabs; `text` is already stress-marked."""
    body = {"text": text, "model_id": LUCY_MODEL, "language_code": "ru", "voice_settings": LUCY_SETTINGS}
    request = urllib.request.Request(f"{ELEVEN_API}/text-to-speech/{LUCY_VOICE}?output_format=mp3_44100_128",
                                     data=json.dumps(body, ensure_ascii=False).encode(), method="POST",
                                     headers={"xi-api-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.read(), "audio/mpeg"
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{LUCY_MODEL}: HTTP {exc.code} {exc.read().decode(errors='replace')[:300]}") from None


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
    ap.add_argument("--engine", choices=["elevenlabs", "openrouter"], default="elevenlabs",
                    help="elevenlabs: Lucy's cloned voice (campaign default); openrouter: --model/--voice")
    ap.add_argument("--model", default="google/gemini-3.8-flash-tts")
    ap.add_argument("--voice", default="Sulafat")
    ap.add_argument("--style", default=STYLE, help="delivery direction; empty to send none")
    ap.add_argument("--samples", action="store_true", help="voice the reel with every voice in SAMPLES")
    ap.add_argument("--stress", action="store_true", help="print the stress-marked text and missing words")
    ap.add_argument("--check", action="store_true", help="read the takes back with Whisper")
    args = ap.parse_args()

    text = " ".join(vo_lines(args.reel))
    if args.stress:
        print(mark(text))
        gaps = missing(text)
        print(f"missing in stress-ru.tsv: {', '.join(gaps)}" if gaps else "every word has its stress")
        return
    takes = []
    if args.engine == "elevenlabs" and not args.samples:
        gaps = missing(text)
        if gaps:
            sys.exit(f"Add stress for these words to ads/audio/stress-ru.tsv first: {', '.join(gaps)}")
        take = save(*speak_lucy(mark(text), api_key("ELEVENLABS_API_KEY")), VO / f"{args.reel}-tts.wav")
        print(f"{take.relative_to(ADS.parent)}: {seconds(take):.1f}s ({LUCY_MODEL}, Lucy)")
        if args.check:
            read_back([take], text)
        return

    key = api_key()
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
