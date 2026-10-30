"""
Правка распознанного текста: детерминированный слой (глоссарий) + опциональный LLM.

Whisper на профлексике курса ошибается системно: «фольга» искажена в 13 из 54
упоминаний (фалгии, фальгу, фолька, фалюка), «полимеризоваться» — в 5 из 7,
«голографическая» — в 3 из 3. Ошибки трогают и основу, и окончание, поэтому
сопоставление идёт по полной словоформе, а не по стему.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

from paths import glossary_path

# Правится ТОЛЬКО слово, которого нет в морфологическом словаре русского.
# Без этого предохранителя нечёткое сопоставление разносит текст: на корпусе
# уроков оно 39 раз меняло «покрываем» на «перекрываем», 29 раз «сразу» на
# «страз» и превращало «прозрачный» в «полупрозрачный». Настоящие слова
# трогать нельзя, сколь угодно похожи они ни были на термин.
MIN_LEN = 5
MIN_RATIO = 0.78
MAX_LEN_DELTA = 4
# Если окончание уцелело и испорчены только буквы внутри слова, склонять не нужно —
# достаточно взять ближайшую словоформу («пидментированный» -> «пигментированный»).
KEEP_FORM_RATIO = 0.90

ADJECTIVE_ENDINGS = [
    "ый", "ий", "ой", "ая", "яя", "ое", "ее", "ые", "ие",
    "ого", "его", "ому", "ему", "ым", "им", "ых", "их", "ыми", "ими",
    "ую", "юю", "ей", "ом", "ем",
]

_WORD_RE = re.compile(r"[А-Яа-яЁёA-Za-z][А-Яа-яЁёA-Za-z-]*")

_MORPH: Any = None
_KNOWN_CACHE: dict[str, bool] = {}


def _morph() -> Any:
    """Морфологический анализатор. None, если pymorphy3 недоступен."""
    global _MORPH
    if _MORPH is None:
        try:
            import pymorphy3
            _MORPH = pymorphy3.MorphAnalyzer()
        except Exception:
            _MORPH = False
    return _MORPH or None


def is_known_word(word: str) -> bool:
    """Есть ли слово в словаре русского. Неизвестные — кандидаты на правку."""
    key = word.lower()
    hit = _KNOWN_CACHE.get(key)
    if hit is None:
        m = _morph()
        # без pymorphy предохранителя нет — тогда правим только по явным спискам
        hit = True if m is None else bool(m.word_is_known(key))
        _KNOWN_CACHE[key] = hit
    return hit


def paradigm(lemma: str) -> list[str]:
    """Все словоформы леммы. Пусто, если анализатор не знает слова."""
    m = _morph()
    if m is None:
        return []
    parses = m.parse(lemma)
    if not parses or not m.word_is_known(lemma):
        return []
    return sorted({f.word for f in parses[0].lexeme})


def _safe_paradigm(lemma: str) -> list[str]:
    """Предсказанная парадигма, очищенная от форм с чужой основой."""
    m = _morph()
    if m is None:
        return []
    try:
        forms = [f.word for f in m.parse(lemma)[0].lexeme]
    except Exception:
        return []
    prefix = _norm(lemma)[: max(4, len(_norm(lemma)) - 2)]
    return [f for f in forms if _norm(f).startswith(prefix)]


def _grammemes(tag: Any) -> list[set[str]]:
    """Наборы граммем от полного к урезанному — для последовательных попыток."""
    parts = [tag.case, tag.number, tag.gender, tag.tense, tag.person, tag.mood]
    full = {g for g in parts if g}
    tries = [full]
    if tag.case and tag.number:
        tries.append({tag.case, tag.number})
    if tag.case:
        tries.append({tag.case})
    if tag.number:
        tries.append({tag.number})
    return [t for t in tries if t]


def _inflection_is_sane(lemma: str, result: str) -> bool:
    """
    Отсеять развалившиеся склонения. Анализатор склоняет «гель-лак» по обеим
    частям («гелем-лаком») и умеет выдумывать формы вроде «полимеризоватимся».
    """
    if not result:
        return False
    key, lemma_key = _norm(result), _norm(lemma)
    prefix = lemma_key[: max(4, min(len(lemma_key) - 2, 5))]
    if not key.startswith(prefix):
        return False
    # форма несуществующего слова при известной лемме — выдумка анализатора
    if is_known_word(lemma) and not is_known_word(result):
        return False
    return True


def inflect_like(lemma: str, corrupted: str) -> str | None:
    """
    Поставить канонический термин в ту же форму, в какой стоит искажённое слово.
    Без этого замена берёт ближайшую строку и ломает падеж: «праймерах» -> «праймера».
    """
    m = _morph()
    if m is None:
        return None
    src = m.parse(corrupted)
    dst = m.parse(lemma)
    if not src or not dst:
        return None
    src_pos = src[0].tag.POS
    for target in dst:
        # часть речи должна совпасть, иначе это просто похожее слово
        if target.tag.POS != src_pos:
            continue
        for gram in _grammemes(src[0].tag):
            try:
                result = target.inflect(gram)
            except Exception:
                result = None
            if result:
                return result.word
        return target.word
    return None


@dataclass
class Edit:
    kind: str          # phrase | fuzzy | llm
    before: str
    after: str
    index: int
    ratio: float = 0.0
    context: str = ""


@dataclass
class Vocabulary:
    forms: dict[str, str] = field(default_factory=dict)        # ключ словоформы -> лемма
    written: dict[str, str] = field(default_factory=dict)      # ключ словоформы -> написание
    never: set[str] = field(default_factory=set)
    by_initial: dict[str, list[str]] = field(default_factory=dict)

    def add(self, form: str, lemma: str) -> None:
        key = _norm(form)
        if not key or key in self.forms:
            return
        self.forms[key] = lemma
        self.written[key] = form
        self.by_initial.setdefault(key[0], []).append(key)


def _norm(word: str) -> str:
    """Ключ сравнения: нижний регистр, ё=е, дефис убран."""
    return word.lower().replace("ё", "е").replace("-", "").strip()


def expand_adjective(stem: str) -> list[str]:
    return [stem + end for end in ADJECTIVE_ENDINGS]


def load_glossary(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or glossary_path()).read_text(encoding="utf-8"))


def build_vocabulary(glossary: dict[str, Any]) -> Vocabulary:
    vocab = Vocabulary(never={_norm(w) for w in glossary.get("never_touch", [])})
    # Рукописный список + парадигма от анализатора. Предсказание для заимствований
    # обычно верное (праймер, стемпинг, шиммер), но иногда разваливает слово
    # («гель-лак» -> «геля-лака», «бондер» -> «бондёр»), поэтому берём только те
    # формы, что начинаются с основы леммы.
    for lemma, forms in glossary.get("nouns", {}).items():
        for form in forms:
            vocab.add(form, lemma)
        for form in _safe_paradigm(lemma):
            vocab.add(form, lemma)
    for lemma, forms in glossary.get("verbs", {}).items():
        for form in forms:
            vocab.add(form, lemma)
        for form in _safe_paradigm(lemma):
            vocab.add(form, lemma)
    for stem in glossary.get("adjectives", {}):
        lemma = stem + "ый"
        for form in expand_adjective(stem):
            vocab.add(form, lemma)
    return vocab


def best_match(word: str, vocab: Vocabulary) -> tuple[str, float] | None:
    """Ближайшая словоформа глоссария или None, если правка не нужна."""
    key = _norm(word)
    if len(key) < MIN_LEN or key in vocab.never:
        return None
    if key in vocab.forms:
        return None  # уже верно
    if is_known_word(word):
        return None  # настоящее русское слово — не наше дело
    bucket = vocab.by_initial.get(key[0])
    if not bucket:
        return None
    best_key, best_ratio = "", 0.0
    matcher = SequenceMatcher()
    matcher.set_seq2(key)
    for cand in bucket:
        if abs(len(cand) - len(key)) > MAX_LEN_DELTA:
            continue
        matcher.set_seq1(cand)
        if matcher.real_quick_ratio() <= best_ratio or matcher.quick_ratio() <= best_ratio:
            continue
        ratio = matcher.ratio()
        if ratio > best_ratio:
            best_key, best_ratio = cand, ratio
    if best_ratio < MIN_RATIO:
        return None
    lemma = vocab.forms[best_key]
    closest = vocab.written.get(best_key, lemma)

    # 1) окончание цело — правим только буквы, падеж уже верный
    if best_ratio >= KEEP_FORM_RATIO:
        return closest, best_ratio

    # 2) окончание тоже испорчено — ставим термин в форму искажённого слова
    inflected = inflect_like(lemma, word)
    if inflected and _inflection_is_sane(lemma, inflected):
        return inflected, best_ratio

    # 3) склонение не удалось: при разных частях речи похожесть случайна
    if _morph() is not None and m_pos_differs(lemma, word):
        return None
    return closest, best_ratio


def m_pos_differs(lemma: str, word: str) -> bool:
    """Разные части речи — верный признак, что похожесть случайна."""
    m = _morph()
    if m is None:
        return False
    a = m.parse(lemma)
    b = m.parse(word)
    if not a or not b:
        return False
    return a[0].tag.POS != b[0].tag.POS


def _match_case(source: str, replacement: str) -> str:
    if source.isupper() and len(source) > 1:
        return replacement.upper()
    if source[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def fix_text(text: str, vocab: Vocabulary) -> tuple[str, list[Edit]]:
    """Нечёткая правка обычной строки — для аудита по старым транскриптам."""
    edits: list[Edit] = []

    def repl(m: re.Match[str]) -> str:
        word = m.group(0)
        hit = best_match(word, vocab)
        if not hit:
            return word
        fixed, ratio = hit
        fixed = _match_case(word, fixed)
        if fixed != word:
            edits.append(Edit("fuzzy", word, fixed, m.start(), ratio))
        return fixed

    return _WORD_RE.sub(repl, text), edits


# ---------------------------------------------------------------- слова и время

def _split_token(token: str) -> tuple[str, str, str]:
    """Разбить токен на ведущие символы, само слово и хвостовую пунктуацию."""
    m = _WORD_RE.search(token)
    if not m:
        return token, "", ""
    return token[: m.start()], m.group(0), token[m.end():]


def _redistribute(words: list[dict], new_texts: list[str]) -> list[dict]:
    """Заменить отрезок слов новыми, разложив время пропорционально длине."""
    if not new_texts:
        return []
    start = words[0]["start"]
    end = words[-1]["end"]
    span = max(end - start, 1e-3)
    total = sum(max(len(t.strip()), 1) for t in new_texts)
    out: list[dict] = []
    cursor = start
    prob = min((w.get("prob", 1.0) for w in words), default=1.0)
    for i, text in enumerate(new_texts):
        share = span * max(len(text.strip()), 1) / total
        w_end = end if i == len(new_texts) - 1 else cursor + share
        out.append({"w": text, "start": round(cursor, 3), "end": round(w_end, 3), "prob": prob})
        cursor = w_end
    return out


def normalize_words(words: list[dict]) -> list[dict]:
    """
    Склеить обрывки, которые Whisper выдаёт отдельными токенами: «все» + «-таки»,
    «гель» + «-лака», «3» + «-5». Иначе в титре остаётся пробел перед дефисом.
    """
    out: list[dict] = []
    for word in words:
        token = word["w"].strip()
        if not token:
            continue
        glue = token.startswith("-") or not _WORD_RE.search(token)
        if glue and out:
            out[-1] = {**out[-1],
                       "w": out[-1]["w"].rstrip() + token,
                       "end": max(out[-1]["end"], word["end"])}
            continue
        out.append({**word, "w": token})
    return out


def apply_phrases(words: list[dict], glossary: dict[str, Any]) -> tuple[list[dict], list[Edit]]:
    """Многословные замены (гель лак -> гель-лак) с сохранением окончания."""
    rules: list[tuple[list[str], str, bool, str]] = []
    for rule in glossary.get("phrases", []):
        for src in rule["from"]:
            parts = [_norm(p) for p in src.split()]
            if len(parts) > 1:
                rules.append((parts, rule["to"], rule.get("inflect", False), src))
    rules.sort(key=lambda r: -len(r[0]))

    keys = [_norm(_split_token(w["w"])[1]) for w in words]
    out: list[dict] = []
    edits: list[Edit] = []
    i = 0
    while i < len(words):
        matched = False
        for parts, target, inflect, _src in rules:
            n = len(parts)
            if keys[i:i + n] != parts:
                continue
            span = words[i:i + n]
            lead, _first, trail = _split_token(span[0]["w"])
            _, last_word, last_trail = _split_token(span[-1]["w"])
            replacement = target
            if inflect:
                # окончание берём у последнего слова исходной фразы: гель лаком -> гель-лаком
                base_tail = _norm(parts[-1])
                canon_tail = _norm(target.split("-")[-1])
                if base_tail.startswith(canon_tail) and len(base_tail) > len(canon_tail):
                    replacement = target + last_word[len(canon_tail):]
            replacement = _match_case(last_word, replacement)
            new_token = f"{lead}{replacement}{last_trail or trail}"
            out.extend(_redistribute(span, [new_token]))
            edits.append(Edit("phrase", " ".join(w["w"].strip() for w in span), replacement, i))
            i += n
            matched = True
            break
        if not matched:
            out.append(words[i])
            i += 1
    return out, edits


def apply_fuzzy(words: list[dict], vocab: Vocabulary) -> tuple[list[dict], list[Edit]]:
    out: list[dict] = []
    edits: list[Edit] = []
    for idx, word in enumerate(words):
        lead, core, trail = _split_token(word["w"])
        if not core:
            out.append(word)
            continue
        hit = best_match(core, vocab)
        if not hit:
            out.append(word)
            continue
        fixed, ratio = hit
        fixed = _match_case(core, fixed)
        if fixed == core:
            out.append(word)
            continue
        ctx = " ".join(w["w"].strip() for w in words[max(0, idx - 4):idx + 5])
        edits.append(Edit("fuzzy", core, fixed, idx, ratio, ctx))
        out.append({**word, "w": f"{lead}{fixed}{trail}"})
    return out, edits


def correct_words(
    words: list[dict], glossary: dict[str, Any] | None = None
) -> tuple[list[dict], list[Edit]]:
    """Детерминированный слой целиком: фразы, затем нечёткая правка словоформ."""
    glossary = glossary or load_glossary()
    vocab = build_vocabulary(glossary)
    words = normalize_words(words)
    words, phrase_edits = apply_phrases(words, glossary)
    words, fuzzy_edits = apply_fuzzy(words, vocab)
    return words, phrase_edits + fuzzy_edits


def format_report(edits: Iterable[Edit]) -> str:
    rows = list(edits)
    if not rows:
        return "Правок нет.\n"
    lines = [f"Всего правок: {len(rows)}", ""]
    for kind in ("phrase", "fuzzy", "llm"):
        group = [e for e in rows if e.kind == kind]
        if not group:
            continue
        title = {"phrase": "ФРАЗЫ", "fuzzy": "СЛОВОФОРМЫ", "llm": "LLM"}[kind]
        lines.append(f"--- {title} ({len(group)}) ---")
        for e in group:
            score = f"  [{e.ratio:.2f}]" if e.ratio else ""
            lines.append(f"  {e.before!r} -> {e.after!r}{score}")
            if e.context:
                lines.append(f"      … {e.context}")
        lines.append("")
    return "\n".join(lines) + "\n"
