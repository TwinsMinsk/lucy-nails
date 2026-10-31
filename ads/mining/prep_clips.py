"""Cut a reel's shots out of the lessons as square, upscaled, subtitle-free clips.

A shot list lives in ads/campaign/shots/<reel>.json:

    {"reel": "r03", "size": 600, "shots": [
        {"id": "s01-tear", "slug": "folga", "start": 65.5, "end": 68.5, "cx": 980, "cy": 311,
         "speed": 1.0, "size": 600}, ...]}

Every shot is checked before it is cut: the crop square must end above the lesson's
subtitle band (crop_above_band), or the whole shot must be free of subtitles per the
frame-by-frame scan (full_frame_clean). Anything else is refused.

    python ads/mining/prep_clips.py r03 --preview          # sheet with crop squares drawn
    python ads/mining/prep_clips.py r03                    # render with ffmpeg lanczos
    python ads/mining/prep_clips.py r03 --upscale esrgan   # render with Real-ESRGAN x4
    python ads/mining/prep_clips.py r03 --only s01-tear
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from common import ADS, CACHE, clean_bottom, grab_rgb, source
from subs_map import scan

OUT = 1080
FPS = 60  # keep the native 60 fps so the composition can slow shots down without stutter
ESRGAN = ADS / "vendor" / "realesrgan" / "realesrgan-ncnn-vulkan.exe"
FONT = ADS.parent / "scripts" / "subtitles" / "fonts" / "Inter-Medium.ttf"
# Gentle polish after scaling: a touch of sharpening and warmth, nothing a viewer would notice as a filter.
FINISH = "unsharp=5:5:0.6:5:5:0.0,eq=saturation=1.06:contrast=1.03"


def load(reel: str) -> dict:
    return json.loads((ADS / "campaign" / "shots" / f"{reel}.json").read_text(encoding="utf-8"))


def crop_box(shot: dict, default_size: int) -> tuple[int, int, int]:
    size = int(shot.get("size", default_size))
    x = min(max(0, round(shot["cx"] - size / 2)), 1280 - size)
    y = min(max(0, round(shot["cy"] - size / 2)), 720 - size)
    return x, y, size


def clean_mode(shot: dict, box: tuple[int, int, int]) -> str:
    x, y, size = box
    if y + size <= clean_bottom(shot["slug"]):
        return "crop_above_band"
    times, has_text = scan(shot["slug"], shot["start"] - 0.3, shot["end"] + 0.3)
    if not has_text.any():
        return "full_frame_clean"
    first = times[has_text][0]
    raise SystemExit(
        f"{shot['id']}: crop reaches y={y + size} below the clean line {clean_bottom(shot['slug'])} "
        f"and a subtitle is on screen at {first:.1f}s — move the crop up or pick another moment"
    )


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def timing_filters(shot: dict) -> str:
    speed = float(shot.get("speed", 1.0))
    return f"setpts={1 / speed:.4f}*(PTS-STARTPTS),fps={FPS}"


def render_lanczos(shot: dict, box: tuple[int, int, int], out: Path) -> None:
    x, y, size = box
    vf = f"crop={size}:{size}:{x}:{y},{timing_filters(shot)},scale={OUT}:{OUT}:flags=lanczos,{FINISH},format=yuv420p"
    ffmpeg("-ss", f"{shot['start']:.3f}", "-to", f"{shot['end']:.3f}", "-i", str(source(shot["slug"])),
           "-an", "-vf", vf, "-c:v", "libx264", "-preset", "slow", "-crf", "12", str(out))


def render_esrgan(shot: dict, box: tuple[int, int, int], out: Path) -> None:
    x, y, size = box
    with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
        src, up = Path(tmp, "src"), Path(tmp, "up")
        src.mkdir()
        up.mkdir()
        ffmpeg("-ss", f"{shot['start']:.3f}", "-to", f"{shot['end']:.3f}", "-i", str(source(shot["slug"])),
               "-an", "-vf", f"crop={size}:{size}:{x}:{y},{timing_filters(shot)}", str(src / "%05d.png"))
        subprocess.run([str(ESRGAN), "-i", str(src), "-o", str(up), "-n", "realesrgan-x4plus", "-s", "4", "-f", "png"],
                       check=True, capture_output=True, cwd=ESRGAN.parent)
        ffmpeg("-framerate", str(FPS), "-i", str(up / "%05d.png"),
               "-vf", f"scale={OUT}:{OUT}:flags=lanczos,{FINISH},format=yuv420p",
               "-c:v", "libx264", "-preset", "slow", "-crf", "12", str(out))


def preview(spec: dict) -> Path:
    font = ImageFont.truetype(str(FONT), 22)
    cells = []
    for shot in spec["shots"]:
        box = crop_box(shot, spec["size"])
        x, y, size = box
        line = clean_bottom(shot["slug"])
        frames = []
        for t in (shot["start"], (shot["start"] + shot["end"]) / 2, shot["end"] - 0.05):
            img = Image.fromarray(grab_rgb(source(shot["slug"]), t))
            d = ImageDraw.Draw(img)
            d.line([(0, line), (1280, line)], fill=(255, 40, 60), width=3)
            d.rectangle([x, y, x + size, y + size], outline=(60, 220, 120), width=5)
            d.text((12, 8), f"{shot['id']}  {t:.1f}s", fill=(255, 255, 255), font=font, stroke_width=2, stroke_fill=(0, 0, 0))
            frames.append(img.resize((480, 270), Image.LANCZOS))
        row = Image.new("RGB", (480 * 3, 270), (0, 0, 0))
        for i, f in enumerate(frames):
            row.paste(f, (i * 480, 0))
        cells.append(row)
    sheet = Image.new("RGB", (480 * 3, 270 * len(cells)), (0, 0, 0))
    for i, row in enumerate(cells):
        sheet.paste(row, (0, i * 270))
    path = CACHE / "sheets" / f"{spec['reel']}-crops.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, quality=85)
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("reel")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--upscale", choices=["lanczos", "esrgan"], default="lanczos")
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--suffix", default="", help="added to output names, e.g. -esrgan for comparisons")
    args = ap.parse_args()

    spec = load(args.reel)
    if args.preview:
        print(preview(spec))
        return

    out_dir = ADS / "video" / "assets" / "clips" / args.reel
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    for shot in spec["shots"]:
        if args.only and shot["id"] not in args.only:
            continue
        box = crop_box(shot, spec["size"])
        mode = clean_mode(shot, box)
        out = out_dir / f"{shot['id']}{args.suffix}.mp4"
        (render_esrgan if args.upscale == "esrgan" else render_lanczos)(shot, box, out)
        speed = float(shot.get("speed", 1.0))
        manifest[out.name] = {
            "slug": shot["slug"], "start": shot["start"], "end": shot["end"], "crop": list(box),
            "speed": speed, "duration": round((shot["end"] - shot["start"]) / speed, 3),
            "clean_mode": mode, "upscale": args.upscale,
        }
        print(f"{out.name}: {mode}, crop {box}, {args.upscale}")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy(manifest_path, CACHE / f"{args.reel}-manifest.json")


if __name__ == "__main__":
    main()
