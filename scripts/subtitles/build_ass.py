"""
Генерация .ass (для вжигания) и .srt (для правки руками).

ASS, а не SRT, потому что нужны: точное положение от измеренной полосы,
отключение автопереноса (строки ставим сами), разрядка и мягкое появление.
SRT остаётся ведущим редактируемым файлом — .ass всегда пересобирается из него,
поэтому ручная правка текста не может разъехаться со стилем.
"""

from __future__ import annotations

import re
from pathlib import Path

from segment_cues import Cue, layout_lines

FONT_NAME = "Inter Medium"
FONT_SIZE = 34              # ≈4.7% высоты кадра — рекомендованный диапазон для 720p
OUTLINE = 1.4
SHADOW = 1.6
SPACING = 0.4               # лёгкая разрядка: читается заметно ровнее
MARGIN_H = 80
FADE_IN, FADE_OUT = 120, 140
LINE_SPACING_FACTOR = 1.22

PRIMARY = "&H00FFFFFF"      # белый
SECONDARY = "&H00FFFFFF"
OUTLINE_COLOUR = "&HC8140F0F"   # почти чёрный, полупрозрачный — не «мультяшный» контур
BACK_COLOUR = "&H78000000"      # мягкая тень

# Караоке: PrimaryColour — уже прозвучавшее, SecondaryColour — то, что впереди.
# Приглушение задано цветом, а не альфой: \fad управляет альфой всей строки и
# на входе-выходе смазал бы разницу между спетым и неспетым.
KARAOKE_STYLES = {
    "soft":  {"primary": "&H00FFFFFF", "secondary": "&H00BEBEBE"},
    "brand": {"primary": "&H00B98FE8", "secondary": "&H00C8C8C8"},
}
MIN_GAP_CS = 2              # зазор короче 0.02 с в тег не выносим


def margin_v(band_top: int, band_bottom: int, frame_height: int,
             font_size: int = FONT_SIZE) -> int:
    """
    Отступ снизу так, чтобы нижняя строка села по центру матовой полосы.
    Вторая строка при этом уходит выше полосы, на растушёванный градиент —
    там она читается за счёт контура и тени.
    """
    line_height = font_size * LINE_SPACING_FACTOR
    band_height = max(band_bottom - band_top, int(line_height))
    pad = max(6, int((band_height - line_height) / 2))
    return max(8, frame_height - band_bottom + pad)


def _ts_ass(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _ts_srt(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    ms = int(round((s - int(s)) * 1000))
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}"


def karaoke_text(cue: Cue) -> str | None:
    """
    Текст реплики с тегами караоке. None — если пословных таймкодов нет или они
    не бьются со строками; тогда реплика рисуется обычной.

    Две тонкости, обе проверены на рендере:
      * караоке-часы стартуют с начала реплики, а не с первого слова, поэтому
        зазор до первого слова выносится в пустой тег — без него заливка бежит
        впереди голоса (на первой реплике урока это полсекунды, два слова);
      * паузы между словами тоже выносятся в пустые теги, иначе заливка
        размазывается по молчанию и к концу фразы накапливает отставание.
    """
    words = cue.words
    if not words:
        return None
    if sum(len(line.split()) for line in cue.lines) != len(words):
        return None

    def cs(seconds: float) -> int:
        return int(round(seconds * 100))

    out_lines: list[str] = []
    index = 0
    cursor = cue.start                      # докуда уже «оплачено» тегами
    for line in cue.lines:
        count = len(line.split())
        parts: list[str] = []
        for position in range(count):
            word = words[index]
            index += 1
            # Границы слова прижимаем к реплике: у последнего слова конец лежит
            # за её пределами (реплика обрезана зазором до следующей), и без
            # этого заливка не успевает дойти до конца строки перед исчезновением.
            word_start = min(max(word["start"], cue.start), cue.end)
            word_end = min(max(word["end"], word_start), cue.end)
            gap = cs(word_start - cursor)
            prefix = ""
            if gap >= MIN_GAP_CS:
                prefix = f"{{\\k{gap}}}"
                cursor += gap / 100
            duration = max(1, cs(word_end - cursor))
            # Пробел ставим внутрь слова, а не через join: иначе он оказывается
            # отдельным символом после пустого тега и сдвигает всю строку вправо.
            tail = " " if position < count - 1 else ""
            parts.append(f"{prefix}{{\\kf{duration}}}{word['w']}{tail}")
            cursor += duration / 100
        out_lines.append("".join(parts))
    return "\\N".join(out_lines)


def build_ass(cues: list[Cue], width: int, height: int, margin_bottom: int,
              font_size: int = FONT_SIZE, karaoke: str | None = None) -> str:
    palette = KARAOKE_STYLES.get(karaoke or "", {})
    primary = palette.get("primary", PRIMARY)
    secondary = palette.get("secondary", SECONDARY)
    head = f"""[Script Info]
; Собрано scripts/subtitles — правьте .srt, этот файл пересоздаётся
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Lesson,{FONT_NAME},{font_size},{primary},{secondary},{OUTLINE_COLOUR},{BACK_COLOUR},0,0,0,0,100,100,{SPACING},0,1,{OUTLINE},{SHADOW},2,{MARGIN_H},{MARGIN_H},{margin_bottom},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [head]
    plain = 0
    for cue in cues:
        text = karaoke_text(cue) if karaoke else None
        if text is None:
            text = "\\N".join(cue.lines)
            plain += 1
        lines.append(
            f"Dialogue: 0,{_ts_ass(cue.start)},{_ts_ass(cue.end)},Lesson,,0,0,0,,"
            f"{{\\fad({FADE_IN},{FADE_OUT})}}{text}"
        )
    if karaoke and plain:
        lines.insert(1, f"; без караоке осталось реплик: {plain} (нет пословных таймкодов)")
    return "\n".join(lines) + "\n"


def build_srt(cues: list[Cue]) -> str:
    blocks = []
    for i, cue in enumerate(cues, 1):
        blocks.append(f"{i}\n{_ts_srt(cue.start)} --> {_ts_srt(cue.end)}\n"
                      + "\n".join(cue.lines))
    return "\n\n".join(blocks) + "\n"


_SRT_TIME = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{1,3})"
)


def parse_srt(text: str) -> list[Cue]:
    """
    Прочитать отредактированный .srt. Строки переразбиваются заново, чтобы
    ручная правка не нарушила лимиты по длине строки.
    """
    cues: list[Cue] = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()):
        rows = [r for r in block.split("\n") if r.strip()]
        if not rows:
            continue
        m = None
        body_start = 0
        for idx, row in enumerate(rows[:2]):
            m = _SRT_TIME.search(row)
            if m:
                body_start = idx + 1
                break
        if not m:
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2 = (int(g) for g in m.groups())
        start = h1 * 3600 + m1 * 60 + s1 + ms1 / (1000 if len(m.group(4)) == 3 else 100)
        end = h2 * 3600 + m2 * 60 + s2 + ms2 / (1000 if len(m.group(8)) == 3 else 100)
        body = " ".join(rows[body_start:]).strip()
        if not body:
            continue
        cues.append(Cue(start=round(start, 3), end=round(end, 3), lines=layout_lines(body)))
    return cues


def attach_words(cues: list[Cue], words: list[dict]) -> list[Cue]:
    """
    Вернуть репликам пословные таймкоды после правки .srt.

    В .srt пословного времени нет, а караоке без него не собрать. Берём слова,
    попадающие в окно реплики, и выравниваем их с отредактированным текстом —
    совпавшие слова сохраняют исходное время, дописанные получают его
    пропорционально длине.
    """
    from llm_polish import realign

    position = 0
    for cue in cues:
        start_index = position
        while start_index < len(words) and words[start_index]["end"] <= cue.start + 0.02:
            start_index += 1
        end_index = start_index
        while end_index < len(words) and words[end_index]["start"] < cue.end - 0.02:
            end_index += 1
        chunk = words[start_index:end_index]
        position = max(end_index, start_index)
        cue.words = realign(chunk, cue.text) if chunk else []
    return cues


def write_subtitles(cues: list[Cue], out_dir: Path, slug: str, *,
                    width: int, height: int, margin_bottom: int,
                    font_size: int = FONT_SIZE, write_srt: bool = True,
                    karaoke: str | None = None) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ass_path = out_dir / f"{slug}.ass"
    ass_path.write_text(build_ass(cues, width, height, margin_bottom, font_size, karaoke),
                        encoding="utf-8")
    written = {"ass": ass_path}
    if write_srt:
        srt_path = out_dir / f"{slug}.srt"
        srt_path.write_text(build_srt(cues), encoding="utf-8")
        written["srt"] = srt_path
    return written
