"""
Сборка видео в два прохода.

Проход A делает мастер: цветокор и матовая плашка поверх старых титров, но БЕЗ
текста. Проход B вжигает в этот мастер .ass. Разрез проходит ровно по границе
«картинка / текст», поэтому правка субтитров стоит один короткий проход, а не
полный пересчёт.

Порядок внутри прохода A принципиален: грейд идёт ДО плашки (иначе плашка
поплывёт по цвету вместе с картинкой), а текст — после всего, иначе деноиз и
шарп начнут жевать буквы.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from paths import repo_root

BLUR_SIGMA = 22             # при такой силе белый текст 34px пропадает полностью
BLUR_STEPS = 3
BLUR_DARKEN = -0.03
BLUR_DESATURATE = 0.94
FEATHER = 44                # растушёвка верхней кромки плашки, px — идёт выше полосы
BAND_LIFT = 6               # запас над найденной полосой
SCRIM_HEIGHT = 160          # мягкое затемнение под текстом
SCRIM_ALPHA = 0.26
SCRIM_RGB = (30, 26, 28)

MASTER_CRF = 16             # мастер чуть щедрее финала: он переживает второй прогон
FINAL_CRF = 18


@dataclass
class Encoder:
    name: str
    args: list[str]


def encoder(kind: str, crf: int) -> Encoder:
    if kind == "nvenc":
        return Encoder("h264_nvenc", [
            "-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq",
            "-rc", "vbr", "-cq", str(crf + 1), "-b:v", "0",
            "-maxrate", "12M", "-bufsize", "24M",
            "-spatial-aq", "1", "-temporal-aq", "1",
            "-profile:v", "high", "-pix_fmt", "yuv420p",
        ])
    return Encoder("libx264", [
        "-c:v", "libx264", "-crf", str(crf), "-preset", "slow",
        "-profile:v", "high", "-level", "4.1",
        "-x264-params", "aq-mode=3:psy-rd=1.0,0.15",
        "-pix_fmt", "yuv420p",
    ])


COLOUR_ARGS = [
    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
    "-movflags", "+faststart",
]


def make_masks(band: dict, out_dir: Path) -> tuple[Path, Path, int]:
    """
    Полнокадровые маска размытия и градиентный скрим.

    Обе растушёвки начинаются на одной высоте, иначе на кадре появляются две
    кромки вместо одной мягкой. Растушёвка идёт ВЫШЕ полосы: если пустить её
    внутрь, размытие в начале полосы окажется полупрозрачным ровно там, где
    лежит старый текст, и он проступит.
    """
    import numpy as np
    from PIL import Image

    width, height = band["width"], band["height"]
    solid_top = max(0, (band["top"] - BAND_LIFT) // 2 * 2)   # отсюда размытие в полную силу
    feather_top = max(0, solid_top - FEATHER)

    ramp = np.zeros(height, dtype=np.float32)
    if solid_top > feather_top:
        span = np.linspace(0.0, 1.0, solid_top - feather_top, dtype=np.float32)
        ramp[feather_top:solid_top] = span ** 1.6
    ramp[solid_top:] = 1.0

    mask = np.repeat((ramp * 255).astype(np.uint8)[:, None], width, axis=1)
    Image.fromarray(mask, mode="L").save(out_dir_mkdir(out_dir) / "band-mask.png")

    # Скрим тянется от той же высоты до низа кадра, набирая плотность плавно
    scrim_ramp = np.zeros(height, dtype=np.float32)
    if height > feather_top:
        span = np.linspace(0.0, 1.0, height - feather_top, dtype=np.float32)
        scrim_ramp[feather_top:] = span ** 1.35
    alpha = (scrim_ramp * SCRIM_ALPHA * 255).astype(np.uint8)
    scrim = np.zeros((height, width, 4), dtype=np.uint8)
    scrim[:, :, 0], scrim[:, :, 1], scrim[:, :, 2] = SCRIM_RGB
    scrim[:, :, 3] = np.repeat(alpha[:, None], width, axis=1)
    Image.fromarray(scrim, mode="RGBA").save(out_dir / "scrim.png")

    return out_dir / "band-mask.png", out_dir / "scrim.png", feather_top


def out_dir_mkdir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def master_filtergraph(grade_chain: str) -> str:
    """
    Размывается ВЕСЬ кадр, а подставляется только низ по маске. Если размывать
    лишь вырезанную полосу, gblur усредняет её саму по себе, цвет у кромки
    перестаёт совпадать с картинкой выше — и стык видно как проведённую линию.
    """
    return (
        f"[0:v]{grade_chain},split=2[base][src];"
        f"[src]gblur=sigma={BLUR_SIGMA}:steps={BLUR_STEPS},"
        f"eq=brightness={BLUR_DARKEN}:saturation={BLUR_DESATURATE},"
        f"format=yuva420p[blur];"
        f"[1:v]format=gray[mask];"
        f"[blur][mask]alphamerge[blurmasked];"
        f"[base][blurmasked]overlay=0:0:format=auto[banded];"
        f"[banded][2:v]overlay=0:0:format=auto,format=yuv420p[v]"
    )


def _filter_path(path: Path, base: Path) -> str:
    """
    Путь для аргумента фильтра. Экранировать двоеточие диска внутри filtergraph —
    источник вечных проблем: парсер режет строку по двоеточиям. Проще отдать путь
    относительно корня репозитория и запустить ffmpeg оттуда.
    """
    try:
        return path.resolve().relative_to(base).as_posix()
    except ValueError:
        return str(path).replace("\\", "/").replace(":", r"\:")


def _run(cmd: list[str], label: str) -> None:
    print(f"  {label}", flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=str(repo_root()))
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-14:])
        raise RuntimeError(f"ffmpeg упал на шаге «{label}»:\n{tail}")


def render_master(video: Path, band: dict, grade_chain: str, out: Path, work: Path,
                  *, enc: str = "x264", duration: float | None = None) -> Path:
    mask_path, scrim_path, _feather_top = make_masks(band, work)
    cmd = ["ffmpeg", "-y", "-v", "error", "-stats"]
    if duration:
        cmd += ["-t", f"{duration:.2f}"]
    cmd += [
        "-i", str(video), "-i", str(mask_path), "-i", str(scrim_path),
        "-filter_complex", master_filtergraph(grade_chain),
        "-map", "[v]", "-map", "0:a?",
        *encoder(enc, MASTER_CRF).args, *COLOUR_ARGS,
        "-c:a", "copy", str(out),
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    _run(cmd, f"проход A — цветокор и плашка ({encoder(enc, MASTER_CRF).name})")
    return out


def burn_subtitles(master: Path, ass_path: Path, fonts_dir: Path, out: Path,
                   *, enc: str = "x264") -> Path:
    base = repo_root()
    vf = (f"ass=filename={_filter_path(ass_path, base)}"
          f":fontsdir={_filter_path(fonts_dir, base)}")
    cmd = [
        "ffmpeg", "-y", "-v", "error", "-stats", "-i", str(master),
        "-vf", vf, "-map", "0:v:0", "-map", "0:a?",
        *encoder(enc, FINAL_CRF).args, *COLOUR_ARGS,
        "-c:a", "copy", str(out),
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    _run(cmd, f"проход B — вжигание субтитров ({encoder(enc, FINAL_CRF).name})")
    return out


def preview(master: Path, ass_path: Path, fonts_dir: Path, out: Path,
            *, start: float, length: float = 60.0) -> Path:
    base = repo_root()
    cmd = [
        "ffmpeg", "-y", "-v", "error", "-ss", f"{start:.2f}", "-i", str(master),
        "-t", f"{length:.2f}",
        "-vf", (f"ass=filename={_filter_path(ass_path, base)}"
                f":fontsdir={_filter_path(fonts_dir, base)}"),
        "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
        "-pix_fmt", "yuv420p", *COLOUR_ARGS, "-c:a", "aac", "-b:a", "128k", str(out),
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    _run(cmd, "предпросмотр 60 с")
    return out


def stills(video: Path, timestamps: list[float], out_png: Path, cols: int = 2) -> Path:
    """Стоп-кадры финала — проверить плашку и субтитры глазами."""
    from PIL import Image

    shots = []
    for ts in timestamps:
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{ts:.2f}", "-i", str(video),
             "-frames:v", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
            check=True, capture_output=True).stdout
        if not raw:
            continue
        size = _size(video)
        need = size[0] * size[1] * 3
        if len(raw) < need:
            continue
        shots.append(Image.frombytes("RGB", size, raw[:need]))
    if not shots:
        raise RuntimeError("Не удалось собрать стоп-кадры")
    scale = 0.5
    tw, th = int(shots[0].width * scale), int(shots[0].height * scale)
    rows = (len(shots) + cols - 1) // cols
    sheet = Image.new("RGB", (tw * cols, th * rows), (18, 16, 17))
    for i, img in enumerate(shots):
        sheet.paste(img.resize((tw, th), Image.LANCZOS), ((i % cols) * tw, (i // cols) * th))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png, quality=93)
    return out_png


def _size(video: Path) -> tuple[int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(video)],
        check=True, capture_output=True, text=True).stdout.strip()
    w, h = out.split("x")[:2]
    return int(w), int(h)


def probe(video: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format",
         "-print_format", "json", str(video)],
        check=True, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    data = json.loads(out)
    video_stream = next(s for s in data["streams"] if s["codec_type"] == "video")
    audio_stream = next((s for s in data["streams"] if s["codec_type"] == "audio"), {})
    return {
        "width": int(video_stream["width"]),
        "height": int(video_stream["height"]),
        "duration": float(data["format"]["duration"]),
        "video_codec": video_stream["codec_name"],
        "audio_codec": audio_stream.get("codec_name"),
        "audio_frames": audio_stream.get("nb_frames"),
        "size_bytes": int(data["format"]["size"]),
    }
