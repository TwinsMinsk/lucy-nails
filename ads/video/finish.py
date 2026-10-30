"""Finish a rendered reel for Instagram: loudness, fast start, cover, review sheet.

    python ads/video/finish.py r03 ads/out/r03/r03-draft-raw.mp4 --name r03-draft

Writes into ads/out/<reel>/:
  <name>.mp4         audio at -14 LUFS / -1.5 dBTP (two-pass loudnorm), video stream copied
  <name>-cover.jpg   frame 0 (the hook frame doubles as the cover)
  <name>-sheet.jpg   a frame every 0.5 s, for checking that no old subtitle slipped through
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ADS = Path(__file__).resolve().parents[1]
TARGET = {"I": -14.0, "TP": -1.5, "LRA": 11.0}


def run(*args: str) -> str:
    return subprocess.run(["ffmpeg", "-hide_banner", "-y", *args], check=True, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stderr


def loudnorm(src: Path, dst: Path) -> None:
    spec = f"loudnorm=I={TARGET['I']}:TP={TARGET['TP']}:LRA={TARGET['LRA']}"
    log = run("-i", str(src), "-af", spec + ":print_format=json", "-f", "null", "-")
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", log).group(0))
    second = (f"{spec}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
              f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    run("-i", str(src), "-c:v", "copy", "-af", second, "-ar", "48000", "-c:a", "aac", "-b:a", "256k",
        "-movflags", "+faststart", str(dst))


def measure(path: Path) -> str:
    log = run("-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-")
    summary = log[log.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1)
    peak = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary).group(1)
    return f"{i} LUFS, true peak {peak} dBTP"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("reel")
    ap.add_argument("raw", type=Path)
    ap.add_argument("--name", required=True)
    args = ap.parse_args()

    out_dir = ADS / "out" / args.reel
    out_dir.mkdir(parents=True, exist_ok=True)
    final = out_dir / f"{args.name}.mp4"
    loudnorm(args.raw, final)
    run("-i", str(final), "-frames:v", "1", "-q:v", "2", str(out_dir / f"{args.name}-cover.jpg"))
    run("-i", str(final), "-vf", "fps=2,scale=216:384,tile=10x6", "-frames:v", "1", "-q:v", "3",
        str(out_dir / f"{args.name}-sheet.jpg"))
    print(f"{final}: {measure(final)}")


if __name__ == "__main__":
    main()
