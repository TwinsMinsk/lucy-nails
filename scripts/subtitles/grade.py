"""
Мягкий beauty-грейд, построенный по замеру, а не по готовым числам.

Салонный свет у каждого урока свой: где-то жёлтит лампа, где-то ноготь уходит
в синеву от окна. Поэтому точки чёрного и белого и баланс белого считаются по
кадрам конкретного файла, и только «характер» картинки (нежная S-кривая,
vibrance с защитой кожи, шарп по яркости) задан одинаково для всего курса.
"""

from __future__ import annotations

import json
import re
import statistics
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

SAMPLE_FPS = "1/5"
BLACK_PERCENTILE = 0.10     # доля кадров, по которой берём точку чёрного
WHITE_PERCENTILE = 0.90
WB_STRENGTH = 0.60          # 1.0 — стерильно нейтрально, 0.6 — естественно
MAX_WB_GAIN = 1.10          # предохранитель от переусердствования
DENOISE = "hqdn3d=1.2:1.0:5:5"
SHARPEN = "unsharp=5:5:0.42:5:5:0.0"

# Нежная S-кривая: тени чуть подняты, света мягко скручены. Задаётся в долях
# рабочего диапазона между точкой чёрного и точкой белого.
CURVE_SHAPE = [(0.0, 0.0), (0.22, 0.245), (0.5, 0.5), (0.78, 0.79), (1.0, 1.0)]

WB_SAMPLE_W, WB_SAMPLE_H = 320, 180
WB_HIGHLIGHT_QUANTILE = 0.80    # берём верхние 20% по яркости
WB_NEUTRAL_TOLERANCE = 0.22     # и только те, что уже почти серые

_STAT_RE = re.compile(r"lavfi\.signalstats\.(\w+)=([-\d.]+)")


@dataclass
class WhiteBalance:
    r_gain: float
    g_gain: float
    b_gain: float
    pixels: int


@dataclass
class GradeStats:
    frames: int
    y_min: float
    y_max: float
    y_avg: float
    u_avg: float
    v_avg: float
    sat_avg: float


@dataclass
class GradeParams:
    black_in: float
    white_in: float
    r_gain: float
    g_gain: float
    b_gain: float
    stats: dict
    wb_pixels: int = 0


def measure(video: Path) -> GradeStats:
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video),
         "-vf", f"fps={SAMPLE_FPS},signalstats,metadata=print:file=-",
         "-f", "null", "-"],
        check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout

    buckets: dict[str, list[float]] = {}
    for key, value in _STAT_RE.findall(out):
        buckets.setdefault(key, []).append(float(value))
    if not buckets.get("YAVG"):
        raise RuntimeError("signalstats не вернул данных — проверьте файл")

    def pick(key: str, q: float) -> float:
        values = sorted(buckets.get(key, [0.0]))
        idx = min(len(values) - 1, max(0, int(len(values) * q)))
        return values[idx]

    return GradeStats(
        frames=len(buckets["YAVG"]),
        y_min=pick("YMIN", BLACK_PERCENTILE),
        y_max=pick("YMAX", WHITE_PERCENTILE),
        y_avg=statistics.median(buckets["YAVG"]),
        u_avg=statistics.median(buckets.get("UAVG", [128.0])),
        v_avg=statistics.median(buckets.get("VAVG", [128.0])),
        sat_avg=statistics.median(buckets.get("SATAVG", [0.0])),
    )


def measure_white_balance(video: Path) -> WhiteBalance:
    """
    Баланс белого по светлым нейтральным пикселям, а не по среднему кадра.
    Среднее здесь врёт: кадр занимают фиолетовые перчатки, и по нему выходит,
    будто в свете избыток синего. Опорой берём стол и блики — то, что на
    съёмке действительно белое.
    """
    import numpy as np

    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video),
         "-vf", f"fps={SAMPLE_FPS},scale={WB_SAMPLE_W}:{WB_SAMPLE_H}",
         "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
        check=True, capture_output=True).stdout
    frame_bytes = WB_SAMPLE_W * WB_SAMPLE_H * 3
    count = len(raw) // frame_bytes
    if count == 0:
        return WhiteBalance(1.0, 1.0, 1.0, 0)

    px = np.frombuffer(raw[: count * frame_bytes], dtype=np.uint8).reshape(-1, 3).astype(np.float32)
    luma = px @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    candidate = px[luma >= np.quantile(luma, WB_HIGHLIGHT_QUANTILE)]
    if candidate.size == 0:
        return WhiteBalance(1.0, 1.0, 1.0, 0)

    spread = candidate.max(axis=1) - candidate.min(axis=1)
    neutral = candidate[spread <= candidate.mean(axis=1) * WB_NEUTRAL_TOLERANCE]
    if len(neutral) < 500:
        neutral = candidate

    avg = neutral.mean(axis=0)
    grey = float(avg.mean())

    def clamp(gain: float) -> float:
        return float(max(1 / MAX_WB_GAIN, min(MAX_WB_GAIN, gain)))

    gains = [clamp(1.0 + (grey / max(float(c), 1e-3) - 1.0) * WB_STRENGTH) for c in avg]
    return WhiteBalance(round(gains[0], 4), round(gains[1], 4), round(gains[2], 4), int(len(neutral)))


def derive(stats: GradeStats, wb: WhiteBalance | None = None) -> GradeParams:
    """Точки чёрного и белого из signalstats плюс поканальные усиления из замера баланса."""
    black = max(0.0, min(stats.y_min, 40.0)) / 255.0
    white = max(min(stats.y_max, 255.0), 200.0) / 255.0
    # оставляем немного воздуха, чтобы не выбить детали
    black = max(0.0, black - 0.008)
    white = min(1.0, white + 0.004)
    wb = wb or WhiteBalance(1.0, 1.0, 1.0, 0)
    return GradeParams(
        black_in=round(black, 4),
        white_in=round(white, 4),
        r_gain=wb.r_gain,
        g_gain=wb.g_gain,
        b_gain=wb.b_gain,
        stats=asdict(stats),
        wb_pixels=wb.pixels,
    )


def _channel_curve(black: float, white: float, gain: float, strength: float) -> str:
    """
    Точки кривой одного канала: рабочий диапазон растягивается от точки чёрного
    к белой, усиление баланса белого поджимает точку белого этого канала.
    """
    black = black * strength
    white = 1.0 - (1.0 - white) * strength
    gain = 1.0 + (gain - 1.0) * strength
    white = max(black + 0.25, min(1.0, white / max(gain, 1e-3)))
    points = []
    for t, out in CURVE_SHAPE:
        x = min(max(black + t * (white - black), 0.0), 1.0)
        points.append(f"{round(x, 4)}/{round(out, 4)}")
    return " ".join(points)


def _curves(params: GradeParams, strength: float) -> str:
    r = _channel_curve(params.black_in, params.white_in, params.r_gain, strength)
    g = _channel_curve(params.black_in, params.white_in, params.g_gain, strength)
    b = _channel_curve(params.black_in, params.white_in, params.b_gain, strength)
    return "curves=r=" + repr(r).replace('"', "'") + ":g=" + repr(g).replace('"', "'") \
        + ":b=" + repr(b).replace('"', "'")


def filter_chain(params: GradeParams, *, strength: float = 1.0) -> str:
    """
    Промежуточные стадии в 10 битах — на 8 битах кривые дают заметный бэндинг
    на градиентах кожи и на растяжках пигмента.

    Точки чёрного/белого и баланс белого сведены в curves, а не в colorlevels:
    colorlevels в ffmpeg 8.1 при 10-битном входе рушит картинку в чёрное
    (проверено покадрово: R=0.1 G=0.0 B=38 против R=107 G=103 B=132 на входе),
    а curves на той же глубине считает верно.
    """
    return ",".join([
        "format=gbrp10le",
        DENOISE,
        _curves(params, strength),
        f"vibrance=intensity={round(0.12 * strength, 3)}:rbal=0.9:gbal=1.0:bbal=1.05",
        (f"eq=contrast={round(1 + 0.03 * strength, 3)}"
         f":saturation={round(1 + 0.02 * strength, 3)}"
         f":gamma={round(1 + 0.01 * strength, 3)}"),
        SHARPEN,
        "format=yuv420p",
    ])


def _size(video: Path) -> tuple[int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(video)],
        check=True, capture_output=True, text=True).stdout.strip()
    w, h = out.split("x")[:2]
    return int(w), int(h)


def _grab(video: Path, ts: float, width: int, height: int, chain: str | None):
    from PIL import Image

    cmd = ["ffmpeg", "-v", "error", "-ss", f"{ts:.2f}", "-i", str(video), "-frames:v", "1"]
    if chain:
        cmd += ["-vf", chain]
    cmd += ["-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    need = width * height * 3
    if len(raw) < need:
        raise RuntimeError("Кадр не прочитан целиком")
    return Image.frombytes("RGB", (width, height), raw[:need])


def compare_stills(video: Path, chain: str, out_png: Path, count: int = 3) -> Path:
    """Кадры «до/после» встык — грейд утверждается глазами, а не по числам."""
    from PIL import Image, ImageDraw

    duration = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(video)],
        check=True, capture_output=True, text=True).stdout.strip())
    width, height = _size(video)

    rows: list[Image.Image] = []
    for i in range(count):
        ts = duration * (i + 0.5) / count
        before = _grab(video, ts, width, height, None)
        after = _grab(video, ts, width, height, chain)
        pair = Image.new("RGB", (width * 2 + 6, height), (18, 16, 17))
        pair.paste(before, (0, 0))
        pair.paste(after, (width + 6, 0))
        draw = ImageDraw.Draw(pair)
        draw.text((14, 12), "ДО", fill=(255, 255, 255))
        draw.text((width + 20, 12), "ПОСЛЕ", fill=(255, 255, 255))
        rows.append(pair)

    scale = 0.62
    tw, th = int(rows[0].width * scale), int(rows[0].height * scale)
    sheet = Image.new("RGB", (tw, th * len(rows)), (18, 16, 17))
    for i, row in enumerate(rows):
        sheet.paste(row.resize((tw, th), Image.LANCZOS), (0, i * th))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png, quality=93)
    return out_png


def analyse(video: Path, out_json: Path | None = None, *, strength: float = 1.0) -> GradeParams:
    params = derive(measure(video), measure_white_balance(video))
    if out_json:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(params) | {
            "strength": strength,
            "chain": filter_chain(params, strength=strength),
        }
        out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return params


if __name__ == "__main__":
    import argparse

    from paths import lesson_dirs, resolve_lesson

    ap = argparse.ArgumentParser(description="Замерить картинку и собрать цветокор")
    ap.add_argument("--lesson", required=True)
    ap.add_argument("--strength", type=float, default=1.0)
    args = ap.parse_args()

    video, title = resolve_lesson(args.lesson)
    dirs = lesson_dirs(args.lesson)
    params = analyse(video, dirs["work"] / "grade.json", strength=args.strength)
    chain = filter_chain(params, strength=args.strength)
    st = params.stats
    print(f"{title}: кадров {st['frames']}, яркость {st['y_avg']:.0f}, "
          f"U={st['u_avg']:.1f} V={st['v_avg']:.1f}, насыщенность {st['sat_avg']:.1f}")
    print(f"точка чёрного {params.black_in}, белого {params.white_in}, "
          f"баланс R×{params.r_gain} G×{params.g_gain} B×{params.b_gain} "
          f"(по {params.wb_pixels} нейтральным пикселям)")
    print(f"цепочка: {chain}")
    png = compare_stills(video, chain, dirs["qa"] / "grade-ab.png")
    print(f"сравнение до/после: {png}")
