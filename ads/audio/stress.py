"""Mark Russian stress in voice-over text for the TTS model, from the lexicon in stress-ru.tsv.

The lexicon writes "+" before the stressed vowel; the marked text carries a combining acute accent (U+0301)
after that vowel instead, which Eleven v4 reads as the stress. The script text itself stays unmarked:
on-screen captions and Whisper checks keep using scripts.md as is.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

LEXICON = Path(__file__).with_name("stress-ru.tsv")
ACUTE = "́"
VOWELS = "аеёиоуыэюяАЕЁИОУЫЭЮЯ"
WORD = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)*")


def plus_to_acute(marked: str) -> str:
    return re.sub(rf"\+([{VOWELS}])", lambda m: m.group(1) + ACUTE, marked)


@lru_cache(maxsize=1)
def lexicon() -> tuple[dict[str, str], dict[str, str]]:
    """(phrases, words): lower-case key -> marked form with the acute accent."""
    phrases, words = {}, {}
    for raw in LEXICON.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        key, marked = raw.split("\t")
        if key.lower() != marked.replace("+", "").replace("ё", "е").lower() and \
                key.lower().replace("ё", "е") != marked.replace("+", "").replace("ё", "е").lower():
            raise ValueError(f"{LEXICON.name}: {key!r} and {marked!r} spell different words")
        (phrases if " " in key else words)[key.lower()] = plus_to_acute(marked)
    return phrases, words


def _match_case(source: str, marked: str) -> str:
    """Copy the capitalisation of `source` onto `marked` (which has extra accent characters)."""
    out, i = [], 0
    for ch in marked:
        if ch == ACUTE:
            out.append(ch)
            continue
        src = source[i] if i < len(source) else ch
        out.append(ch.upper() if src.isupper() else ch)
        i += 1
    return "".join(out)


def mark(text: str) -> str:
    """Return `text` with stress accents from the lexicon; unknown words are left as they are."""
    phrases, words = lexicon()
    for key, marked in phrases.items():
        pattern = re.compile(rf"(?<![А-Яа-яЁё]){re.escape(key)}(?![А-Яа-яЁё])", re.IGNORECASE)
        text = pattern.sub(lambda m: _match_case(m.group(0), marked), text)

    def word(m: re.Match) -> str:
        w = m.group(0)
        end = m.end()
        if end < len(m.string) and m.string[end] == ACUTE:  # already marked by a phrase
            return w
        if ACUTE in w:
            return w
        marked = words.get(w.lower())
        return _match_case(w, marked) if marked else w

    return re.sub(r"[А-Яа-яЁё́]+(?:-[А-Яа-яЁё́]+)*", word, text)


def missing(text: str) -> list[str]:
    """Words that need a stress entry: two or more vowels, no «ё», not in the lexicon."""
    _, words = lexicon()
    out = []
    for w in WORD.findall(text):
        low = w.lower()
        if "ё" in low or sum(ch in VOWELS for ch in low) < 2 or low in words:
            continue
        if all(sum(ch in VOWELS for ch in part) < 2 for part in low.split("-")):
            continue
        if low not in out:
            out.append(low)
    return out
