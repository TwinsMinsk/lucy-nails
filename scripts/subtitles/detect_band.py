"""
Поиск полосы, в которой лежат вшитые субтитры.

Позиция не задаётся руками: у каждого урока она может отличаться, а ошибка
на десяток пикселей оставит на экране хвост старого текста. Полоса измеряется
по кадрам — титры выдаёт сочетание «очень светлый пиксель рядом с очень тёмным»
(у текста есть контур и тень), которого не даёт ни кожа, ни стол, ни блик.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

SAMPLE_FPS = "1/3"          # кадр каждые 3 секунды
SEARCH_HEIGHT = 260         # ищем в нижней части кадра
BRIGHT = 225                # порог «белый текст»
DARK = 90                   # порог «контур/тень»
NEIGHBOURHOOD = 3           # радиус поиска тёмного соседа, px
ROW_MIN_PIXELS = 4          # сколько текстовых пикселей делают строку «текстовой»
ROW_FLOOR = 0.07            # ниже этого порог не опускаем: фон даёт до 7% кадров
LINE_GAP = 16               # разрыв до 16 строк — межстрочный интервал, а не конец блока
PEAK_SHARE = 0.25           # строка считается титром при 25% от пика профиля
MIN_TEXT_FRAMES = 0.05      # минимальная доля кадров с текстом, иначе считаем, что титров нет
PAD = 10                    # запас сверху и снизу, px


@dataclass
class Band:
    top: int
    bottom: int
    left: int
    right: int
    width: int
    height: int
    frames: int
    frames_with_text: float
    two_line_ratio: float
    coverage: float
    confidence: float

    @property
    def band_height(self) -> int:
        return self.bottom - self.top


def probe_size(video: Path) -> tuple[int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(video)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    w, h = out.split("x")[:2]
    return int(w), int(h)


def sample_frames(video: Path, width: int, height: int, strip: int) -> np.ndarray:
    """Нижняя полоса кадров в оттенках серого: (кадры, strip, width)."""
    top = height - strip
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(video),
        "-vf", f"fps={SAMPLE_FPS},crop={width}:{strip}:0:{top}",
        "-pix_fmt", "gray", "-f", "rawvideo", "-",
    ]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    frame_bytes = width * strip
    count = len(raw) // frame_bytes
    if count == 0:
        raise RuntimeError("Не удалось прочитать ни одного кадра")
    return np.frombuffer(raw[: count * frame_bytes], dtype=np.uint8).reshape(count, strip, width)


def text_mask(frames: np.ndarray) -> np.ndarray:
    """Пиксели, похожие на обведённый текст: яркие и с тёмным соседом рядом."""
    bright = frames >= BRIGHT
    dark = frames <= DARK
    near_dark = np.zeros_like(dark)
    for shift in range(1, NEIGHBOURHOOD + 1):
        near_dark[:, :, shift:] |= dark[:, :, :-shift]
        near_dark[:, :, :-shift] |= dark[:, :, shift:]
        near_dark[:, shift:, :] |= dark[:, :-shift, :]
        near_dark[:, :-shift, :] |= dark[:, shift:, :]
    return bright & near_dark


def detect(video: Path, out_json: Path | None = None) -> Band:
    width, height = probe_size(video)
    strip = min(SEARCH_HEIGHT, height)
    frames = sample_frames(video, width, height, strip)
    mask = text_mask(frames)

    per_frame = mask.sum(axis=(1, 2))
    # порог «в кадре есть текст» — по медиане непустых кадров
    active = per_frame > max(60, np.median(per_frame[per_frame > 0]) * 0.35) if per_frame.any() else per_frame > 1e9
    frames_with_text = float(active.mean())
    if frames_with_text < MIN_TEXT_FRAMES:
        raise RuntimeError(
            f"Текст найден лишь в {frames_with_text:.1%} кадров — похоже, вшитых субтитров нет"
        )

    # Доля кадров, в которых строка содержит текст. Считаем именно долю, а не
    # сумму пикселей: иначе редкая вторая строка тонет на фоне постоянной первой
    # и нижний край полосы обрезается ровно там, где живёт перенос.
    row_has = mask[active].sum(axis=2) >= ROW_MIN_PIXELS
    frac = row_has.mean(axis=0)

    # Порог берём от ПИКА профиля. Титры дают резкую ступень: во «Френче» фон
    # плавно растёт с 5% у верха полосы поиска до 19% у низа кадра (розовые
    # перчатки на светлом фоне дают много контрастных кромок), а строка титра
    # стоит на 92%. Порог от уровня шума попадает ровно в этот наклон и
    # захватывает рабочую зону кадра; порог от медианы профиля, наоборот,
    # растёт вместе с тем, как часто в уроке есть титры. Доля от пика
    # устойчива к обоим случаям.
    peak = float(frac.max())
    row_thr = max(ROW_FLOOR, peak * PEAK_SHARE)
    hot_rows = np.flatnonzero(frac >= row_thr)
    if hot_rows.size == 0:
        raise RuntimeError("Полоса субтитров не выделяется на фоне")

    # Берём самый плотный связный блок, а не крайние горячие строки. Отдельные
    # шумные строки есть и вдали от титров (блик на кромке ногтя, край стола):
    # во «Френче» они растягивали полосу с реальных 18 строк до 128 пикселей,
    # захватывая рабочую зону кадра. Разрывы до LINE_GAP строк считаем
    # межстрочным интервалом, иначе двухстрочный титр обрежется по первой строке.
    blocks: list[list[int]] = [[int(hot_rows[0]), int(hot_rows[0])]]
    for row in hot_rows[1:]:
        if int(row) - blocks[-1][1] <= LINE_GAP:
            blocks[-1][1] = int(row)
        else:
            blocks.append([int(row), int(row)])
    top_local, bottom_local = max(blocks, key=lambda b: float(frac[b[0]:b[1] + 1].sum()))
    bottom_local += 1
    offset = height - strip

    cols = mask[active][:, top_local:bottom_local, :].sum(axis=(0, 1)).astype(float)
    hot_cols = np.flatnonzero(cols >= cols.max() * 0.12) if cols.max() > 0 else np.array([])

    # Диагностика: доля «текстовых» пикселей внутри полосы. Не гарантия чистоты —
    # в знаменатель попадают блики на кромках ногтей по всему кадру, поэтому
    # нормальные значения лежат в диапазоне 70-95%. Реальную чистоту меряют по
    # собранному мастеру (он без нового текста), а не по этому числу.
    inside = float(mask[active][:, top_local:bottom_local, :].sum())
    outside = float(mask[active].sum())
    coverage = round(inside / outside, 4) if outside else 0.0

    heights = []
    for row in row_has:
        idx = np.flatnonzero(row)
        if idx.size:
            heights.append(int(idx[-1] - idx[0] + 1))
    heights_arr = np.array(heights) if heights else np.array([0])
    median_h = float(np.median(heights_arr))
    two_line_ratio = (round(float(np.percentile(heights_arr, 95)) / median_h, 2)
                      if median_h else 0.0)

    band = Band(
        top=max(0, offset + top_local - PAD),
        bottom=min(height, offset + bottom_local + PAD),
        left=max(0, int(hot_cols[0]) - PAD) if hot_cols.size else 0,
        right=min(width, int(hot_cols[-1]) + PAD) if hot_cols.size else width,
        width=width,
        height=height,
        frames=int(frames.shape[0]),
        frames_with_text=round(frames_with_text, 3),
        two_line_ratio=two_line_ratio,
        coverage=coverage,
        confidence=round(float(frac.max() / max(row_thr, 1e-6)), 2),
    )
    if out_json:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(asdict(band), ensure_ascii=False, indent=2), encoding="utf-8")
    return band


def make_qa_image(video: Path, band: Band, out_png: Path, count: int = 6) -> Path:
    """Кадры с обведённой полосой — чтобы глазами проверить, что попали."""
    from PIL import Image, ImageDraw

    duration = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(video)],
        check=True, capture_output=True, text=True).stdout.strip())

    shots: list[Image.Image] = []
    for i in range(count):
        ts = duration * (i + 0.5) / count
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{ts:.2f}", "-i", str(video),
             "-frames:v", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
            check=True, capture_output=True).stdout
        if len(raw) < band.width * band.height * 3:
            continue
        img = Image.frombytes("RGB", (band.width, band.height), raw[: band.width * band.height * 3])
        draw = ImageDraw.Draw(img, "RGBA")
        draw.rectangle([band.left, band.top, band.right, band.bottom],
                       outline=(232, 122, 150, 255), width=3)
        draw.rectangle([0, band.top, band.width, band.bottom], outline=(232, 122, 150, 90), width=1)
        draw.text((12, band.top - 22), f"{ts:.0f} с   полоса {band.top}-{band.bottom} px",
                  fill=(255, 255, 255, 235))
        shots.append(img)

    if not shots:
        raise RuntimeError("Не удалось собрать кадры для проверки")
    cols, scale = 2, 0.5
    tw, th = int(band.width * scale), int(band.height * scale)
    rows_n = (len(shots) + cols - 1) // cols
    sheet = Image.new("RGB", (tw * cols, th * rows_n), (18, 16, 17))
    for i, img in enumerate(shots):
        sheet.paste(img.resize((tw, th), Image.LANCZOS), ((i % cols) * tw, (i // cols) * th))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png, quality=92)
    return out_png


if __name__ == "__main__":
    import argparse

    from paths import lesson_dirs, resolve_lesson

    ap = argparse.ArgumentParser(description="Найти полосу вшитых субтитров")
    ap.add_argument("--lesson", required=True)
    args = ap.parse_args()

    video, title = resolve_lesson(args.lesson)
    dirs = lesson_dirs(args.lesson)
    band = detect(video, dirs["work"] / "band.json")
    png = make_qa_image(video, band, dirs["qa"] / "band-detect.png")
    print(f"{title}: полоса y={band.top}..{band.bottom} ({band.band_height} px), "
          f"x={band.left}..{band.right}, текст в {band.frames_with_text:.0%} кадров, "
          f"две строки: {'да' if band.two_line_ratio else 'нет'}")
    print(f"проверка: {png}")
