"""
Сборка реплик и перенос строк по правилам вещательных субтитров.

Старый транскрипт режется по паузам VAD, поэтому строка обрывается на запятой
(«…но я решила попробовать красный,»), сегмент доходит до 163 символов и 36 секунд,
а скорость чтения — до 61 символа в секунду при норме 17. Здесь текст режется по
синтаксису с жёсткими лимитами длины, длительности и скорости чтения.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

# --- лимиты. Подогнаны под 1280x720 и Inter Medium 34px ---------------------
MAX_CHARS_PER_LINE = 38     # ≈900px ≈70% ширины кадра
MAX_LINES = 2
MAX_CHARS = MAX_CHARS_PER_LINE * MAX_LINES + 1   # +1: строки склеиваются пробелом
MAX_CPS = 17.0              # символов в секунду (стандарт Netflix для русского)
MIN_DUR = 1.2
MAX_DUR = 6.0
MIN_GAP = 0.12
LEAD_IN = 0.08              # титр появляется чуть раньше слова
LEAD_OUT = 0.30             # и держится чуть дольше
SENTENCE_PAUSE = 0.70       # пауза, считающаяся границей предложения
MICRO_DUR = 0.80
MICRO_CHARS = 20
CUT_SNAP = 0.25             # притягивание границы к монтажной склейке
HARD_MIN_DUR = 0.70         # ниже этого реплика читается как мигание
MAX_PUSH = 0.30             # предел сдвига реплики вперёд, чтобы не копилась задержка
MIN_DUR_SOFT = MIN_DUR      # цель; достигается только если есть свободная пауза

PREPOSITIONS = {
    "в", "во", "на", "над", "надо", "под", "подо", "о", "об", "обо", "от", "ото",
    "до", "из", "изо", "из-за", "из-под", "к", "ко", "по", "за", "у", "с", "со",
    "при", "про", "для", "без", "безо", "через", "сквозь", "между", "меж",
    "среди", "около", "возле", "вокруг", "после", "перед", "передо", "пред",
    "ради", "кроме", "вместо", "вдоль", "поперёк", "благодаря", "согласно",
    "вопреки", "насчёт", "ввиду", "вследствие", "начиная",
}
PARTICLES = {"не", "ни", "же", "ж", "бы", "б", "ли", "лишь", "даже", "ведь", "уж", "аж"}
CONJUNCTIONS = {
    "и", "а", "но", "да", "что", "чтобы", "чтоб", "если", "когда", "как", "или",
    "либо", "зато", "однако", "поэтому", "потому", "хотя", "пока", "пусть",
    "будто", "словно", "точно", "ибо", "причём", "притом", "также", "тоже",
    "затем", "значит", "иначе", "раз",
}
# Строка не может заканчиваться этими словами — они тянут за собой следующее
NO_LINE_END = PREPOSITIONS | PARTICLES | CONJUNCTIONS

SENTENCE_END_RE = re.compile(r"[.!?…]+[»\"')\]]*$")
STRONG_PUNCT_RE = re.compile(r"[,;:—–]$")
_WORD_RE = re.compile(r"[А-Яа-яЁёA-Za-z0-9][А-Яа-яЁёA-Za-z0-9-]*")


@dataclass
class Cue:
    start: float
    end: float
    lines: list[str]
    words: list[dict] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(self.lines)

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def cps(self) -> float:
        return len(self.text) / self.duration if self.duration > 0 else 999.0


def _bare(token: str) -> str:
    """Слово без пунктуации и регистра — для проверок по спискам."""
    m = _WORD_RE.search(token)
    return m.group(0).lower().replace("ё", "е") if m else ""


def _text_of(words: Iterable[dict]) -> str:
    return " ".join(w["w"].strip() for w in words if w["w"].strip())


# ----------------------------------------------------------------- предложения

def split_sentences(words: list[dict]) -> list[list[dict]]:
    sentences: list[list[dict]] = []
    current: list[dict] = []
    for i, word in enumerate(words):
        current.append(word)
        token = word["w"].strip()
        ends = bool(SENTENCE_END_RE.search(token))
        gap = words[i + 1]["start"] - word["end"] if i + 1 < len(words) else 0.0
        # Пауза после предлога, частицы или союза границей не считается: человек
        # запнулся, а не закончил мысль. Иначе реплика обрывается на «как» или «то».
        pause_break = gap >= SENTENCE_PAUSE and _bare(token) not in NO_LINE_END
        if ends or pause_break:
            sentences.append(current)
            current = []
    if current:
        sentences.append(current)
    return sentences


# ------------------------------------------------------------- точки разрыва

def _break_score(words: list[dict], i: int, prefer_middle: bool = True) -> float | None:
    """
    Насколько хорошо резать перед словом i. None — резать нельзя.
    Веса: пунктуация > союз > предлог > длина паузы.
    """
    if i <= 0 or i >= len(words):
        return None
    prev_token = words[i - 1]["w"].strip()
    prev_bare = _bare(prev_token)
    next_bare = _bare(words[i]["w"])

    # предлог, частицу или союз нельзя оставлять в конце строки
    if prev_bare in NO_LINE_END:
        return None
    # дефисный термин уже единый токен, но подстрахуемся
    if prev_token.endswith("-"):
        return None

    score = 0.0
    if SENTENCE_END_RE.search(prev_token):
        score += 120.0
    elif STRONG_PUNCT_RE.search(prev_token):
        score += 100.0
    if next_bare in CONJUNCTIONS:
        score += 80.0
    elif next_bare in PREPOSITIONS:
        score += 60.0
    pause = words[i]["start"] - words[i - 1]["end"]
    score += min(55.0, max(0.0, pause) * 110.0)

    if prefer_middle:
        left = len(_text_of(words[:i]))
        right = len(_text_of(words[i:]))
        score -= abs(left - right) * 0.5
    return score


def _best_break(words: list[dict], lo: int, hi: int) -> int | None:
    """Лучшая точка разрыва в диапазоне индексов [lo, hi)."""
    best_i, best_score = None, float("-inf")
    for i in range(max(1, lo), min(len(words), hi)):
        score = _break_score(words, i)
        if score is not None and score > best_score:
            best_i, best_score = i, score
    return best_i


# --------------------------------------------------------------- перенос строк

def layout_lines(text: str) -> list[str]:
    """Разложить текст реплики на 1-2 строки. Верхняя строка не длиннее нижней."""
    lines, _ = layout_lines_checked(text)
    return lines


def layout_lines_checked(text: str) -> tuple[list[str], bool]:
    """
    То же плюс признак «уложились». Лимит по числу символов сам по себе не
    гарантирует, что допустимый перенос существует: текст в 77 символов из
    длинных слов может не делиться на две строки по 38. Поэтому решает раскладка,
    а не счётчик — иначе остаётся аварийный разрыв посреди слова.
    """
    text = " ".join(text.split())
    if len(text) <= MAX_CHARS_PER_LINE:
        return [text], True

    tokens = text.split(" ")
    pseudo = [{"w": t, "start": 0.0, "end": 0.0} for t in tokens]

    best: tuple[float, int] | None = None
    for i in range(1, len(tokens)):
        top = " ".join(tokens[:i])
        bottom = " ".join(tokens[i:])
        if len(top) > MAX_CHARS_PER_LINE or len(bottom) > MAX_CHARS_PER_LINE:
            continue
        score = _break_score(pseudo, i, prefer_middle=False)
        if score is None:
            continue
        # верхняя строка короче — так читается ровнее (Netflix TTSG)
        score -= abs(len(top) - len(bottom)) * 0.6
        if len(top) > len(bottom):
            score -= 8.0
        # одинокое короткое слово на строке смотрится оборванным
        if len(bottom.split()) == 1 and len(bottom) <= 4:
            score -= 40.0
        if len(top.split()) == 1 and len(top) <= 4:
            score -= 25.0
        if best is None or score > best[0]:
            best = (score, i)

    if best is not None:
        idx = best[1]
        return [" ".join(tokens[:idx]), " ".join(tokens[idx:])], True

    # ни одна синтаксически допустимая точка не подошла — берём ближайший к
    # середине пробел, лишь бы обе строки влезли
    mid = len(text) // 2
    candidates = [i for i in range(1, len(tokens))
                  if len(" ".join(tokens[:i])) <= MAX_CHARS_PER_LINE
                  and len(" ".join(tokens[i:])) <= MAX_CHARS_PER_LINE]
    if not candidates:
        # уложить нельзя — сообщаем наверх, чтобы отрезок раздробили ещё раз
        return [text], False
    idx = min(candidates, key=lambda i: abs(len(" ".join(tokens[:i])) - mid))
    return [" ".join(tokens[:idx]), " ".join(tokens[idx:])], True


# --------------------------------------------------------------- сборка реплик

def _fits(words: list[dict]) -> bool:
    text = _text_of(words)
    if len(text) > MAX_CHARS:
        return False
    lines, ok = layout_lines_checked(text)
    if not ok or len(lines) > MAX_LINES or any(len(l) > MAX_CHARS_PER_LINE for l in lines):
        return False
    dur = words[-1]["end"] - words[0]["start"] + LEAD_OUT
    if dur > MAX_DUR:
        return False
    # Скорость чтения здесь намеренно не проверяется: дробление делит пополам
    # и текст, и время, поэтому CPS не меняется. Её лечит _relax_cps() —
    # растягиванием реплики в соседнюю паузу.
    return True


def _split_chunk(words: list[dict]) -> list[list[dict]]:
    """Рекурсивно резать отрезок, пока каждый кусок не уложится в лимиты."""
    if len(words) <= 1 or _fits(words):
        return [words]
    idx = _best_break(words, 1, len(words))
    if idx is None:
        # Синтаксически допустимых точек нет. Идём от середины наружу и берём
        # первую позицию, которая хотя бы не обрывает реплику на предлоге,
        # частице или союзе — иначе следующая начнётся с висящего хвоста.
        mid = max(1, len(words) // 2)
        idx = mid
        for shift in range(0, len(words)):
            for cand in (mid - shift, mid + shift):
                if 1 <= cand < len(words) and _bare(words[cand - 1]["w"]) not in NO_LINE_END:
                    idx = cand
                    break
            else:
                continue
            break
    left, right = words[:idx], words[idx:]
    if not left or not right:
        return [words]
    return _split_chunk(left) + _split_chunk(right)


def build_cues(words: list[dict], scene_cuts: list[float] | None = None) -> list[Cue]:
    words = [w for w in words if w["w"].strip()]
    if not words:
        return []

    chunks: list[list[dict]] = []
    for sentence in split_sentences(words):
        chunks.extend(_split_chunk(sentence))

    chunks = _merge_micro(chunks)

    cues = [Cue(start=c[0]["start"], end=c[-1]["end"], lines=layout_lines(_text_of(c)), words=c)
            for c in chunks if c]
    cues = _dedupe(cues)
    _apply_timing(cues)
    _relax_cps(cues)
    if scene_cuts:
        _snap_to_cuts(cues, scene_cuts)
    return cues


def _merge_micro(chunks: list[list[dict]]) -> list[list[dict]]:
    """Слить слишком короткие обрывки с соседом, если вместе они влезают."""
    out: list[list[dict]] = []
    pending: list[dict] = []
    for chunk in chunks:
        if pending:
            chunk = pending + chunk
            pending = []
        text = _text_of(chunk)
        dur = chunk[-1]["end"] - chunk[0]["start"]
        is_micro = dur < MICRO_DUR and len(text) < MICRO_CHARS
        if is_micro and out:
            merged = out[-1] + chunk
            # Обрывок вроде «Для» или «После» — начало следующего предложения.
            # Приклеив его назад, получим реплику, обрывающуюся на предлоге;
            # такой хвост повисает в кадре. Переносим обрывок вперёд.
            if _fits(merged) and not _ends_badly(merged):
                out[-1] = merged
                continue
            if _ends_badly(chunk):
                pending = chunk
                continue
        out.append(chunk)
    if pending:
        out.append(pending)
    return out


def _ends_badly(words: list[dict]) -> bool:
    """Отрезок кончается предлогом, частицей или союзом — но не концом предложения."""
    if not words:
        return False
    token = words[-1]["w"].strip()
    if SENTENCE_END_RE.search(token):
        return False
    return _bare(token) in NO_LINE_END


def _natural_bounds(cue: Cue) -> tuple[float, float]:
    return max(0.0, cue.words[0]["start"] - LEAD_IN), cue.words[-1]["end"] + LEAD_OUT


def _apply_timing(cues: list[Cue]) -> None:
    """
    Тайминги ставятся по словам, а не по сетке. Минимальная длительность здесь —
    цель, а не закон: дотягиваем только за счёт свободной паузы. Иначе на плотной
    речи титры поехали бы относительно голоса, а рассинхрон заметнее короткой реплики.
    """
    n = len(cues)
    for cue in cues:
        cue.start, cue.end = _natural_bounds(cue)

    for i, cue in enumerate(cues):
        nat_start, nat_end = _natural_bounds(cue)
        if i:
            prev_end = cues[i - 1].end
            # сдвиг вперёд ограничен, чтобы задержка не копилась по цепочке
            cue.start = min(max(nat_start, prev_end + MIN_GAP), nat_start + MAX_PUSH)
            cue.start = max(cue.start, prev_end + 0.02)
        else:
            cue.start = max(0.0, nat_start)

        ceiling = (
            _natural_bounds(cues[i + 1])[0] - MIN_GAP
            if i + 1 < n
            else cue.start + MAX_DUR
        )
        target_end = max(nat_end, cue.start + MIN_DUR_SOFT)
        cue.end = min(target_end, max(ceiling, cue.start + HARD_MIN_DUR))
        cue.end = min(cue.end, cue.start + MAX_DUR)
        if cue.end <= cue.start:
            cue.end = cue.start + HARD_MIN_DUR

        cue.start = round(cue.start, 3)
        cue.end = round(cue.end, 3)


def _relax_cps(cues: list[Cue]) -> None:
    """
    Скорость чтения лечится растягиванием реплики в соседнюю паузу, а не
    дроблением: дробление делит пополам и текст, и время, поэтому CPS не меняет.
    """
    n = len(cues)
    for i, cue in enumerate(cues):
        if cue.cps <= MAX_CPS:
            continue
        needed = len(cue.text) / MAX_CPS
        ceiling = (cues[i + 1].start - MIN_GAP) if i + 1 < n else cue.start + MAX_DUR
        cue.end = round(min(max(cue.end, cue.start + needed), max(ceiling, cue.end),
                            cue.start + MAX_DUR), 3)
        if cue.cps <= MAX_CPS:
            continue
        floor = (cues[i - 1].end + MIN_GAP) if i else 0.0
        cue.start = round(max(min(cue.start, cue.end - needed), floor), 3)


def _dedupe(cues: list[Cue]) -> list[Cue]:
    """Убрать повторы подряд — Whisper иногда выдаёт один и тот же кусок дважды."""
    out: list[Cue] = []
    for cue in cues:
        if out and out[-1].text == cue.text and cue.start - out[-1].end < 2.0:
            out[-1].end = max(out[-1].end, min(cue.end, out[-1].start + MAX_DUR))
            continue
        out.append(cue)
    return out


def _snap_to_cuts(cues: list[Cue], cuts: list[float]) -> None:
    """Не давать титру переезжать через монтажную склейку."""
    if not cuts:
        return
    for cue in cues:
        for cut in cuts:
            if cue.start < cut < cue.end:
                # склейка почти в конце — подтянуть конец назад
                if cue.end - cut <= CUT_SNAP and cut - cue.start >= MIN_DUR:
                    cue.end = round(cut - 0.02, 3)
                # склейка почти в начале — сдвинуть начало вперёд
                elif cut - cue.start <= CUT_SNAP and cue.end - cut >= MIN_DUR:
                    cue.start = round(cut + 0.02, 3)


# ------------------------------------------------------------------- статистика

def cue_stats(cues: list[Cue]) -> dict[str, Any]:
    if not cues:
        return {}
    line_lens = [len(line) for cue in cues for line in cue.lines]
    texts = [cue.text for cue in cues]
    durs = [cue.duration for cue in cues]
    cpss = [cue.cps for cue in cues]
    return {
        "cues": len(cues),
        "max_lines": max(len(c.lines) for c in cues),
        "line_chars_max": max(line_lens),
        "line_chars_median": sorted(line_lens)[len(line_lens) // 2],
        "cue_chars_max": max(len(t) for t in texts),
        "dur_min": round(min(durs), 2),
        "dur_max": round(max(durs), 2),
        "dur_median": round(sorted(durs)[len(durs) // 2], 2),
        "cps_max": round(max(cpss), 1),
        "cps_median": round(sorted(cpss)[len(cpss) // 2], 1),
        # Считаем только БЛИЗКИЕ повторы: их даёт петля Whisper. Одна и та же
        # фраза через минуту — обычная речь («и отправляю сушиться в лампу»).
        "duplicates": sum(
            1 for i in range(1, len(cues))
            if cues[i].text == cues[i - 1].text and cues[i].start - cues[i - 1].end < 10.0
        ),
    }


def check_cues(cues: list[Cue]) -> list[str]:
    """Нарушения стандарта. Пустой список — всё в норме."""
    problems: list[str] = []
    for i, cue in enumerate(cues):
        if len(cue.lines) > MAX_LINES:
            problems.append(f"#{i}: строк {len(cue.lines)} > {MAX_LINES}")
        for line in cue.lines:
            if len(line) > MAX_CHARS_PER_LINE:
                problems.append(f"#{i}: строка {len(line)} символов > {MAX_CHARS_PER_LINE}: {line!r}")
            # Конец предложения не считается: «можно без.», «ещё раз.»,
            # «то, что надо.» — там слово стоит законно, просто оно омоним
            # предлога или союза.
            if (len(cue.lines) > 1 and not SENTENCE_END_RE.search(line)
                    and _bare(line.split()[-1]) in NO_LINE_END):
                problems.append(f"#{i}: строка кончается служебным словом: {line!r}")
        if cue.duration < HARD_MIN_DUR - 0.01:
            problems.append(f"#{i}: длительность {cue.duration:.2f} < {HARD_MIN_DUR}")
        if cue.duration > MAX_DUR + 0.01:
            problems.append(f"#{i}: длительность {cue.duration:.2f} > {MAX_DUR}")
        if cue.cps > MAX_CPS + 0.5:
            problems.append(f"#{i}: скорость чтения {cue.cps:.1f} > {MAX_CPS}")
        if i and cue.start < cues[i - 1].end - 0.001:
            problems.append(f"#{i}: перекрывает предыдущую реплику")
    return problems
