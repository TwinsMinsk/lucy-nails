"""
Второй слой правки текста: языковая модель чинит то, чего не берёт глоссарий.

Детерминированный слой ловит искажения известных терминов, но бессилен там, где
Whisper подменил обычное слово похожим по звучанию: «которую мы для себя
придерели» вместо «определили». Такие места видны только по смыслу фразы.

Модель работает под жёсткими рамками: порядок слов не менять, фактов не
добавлять, не перефразировать. Результат проверяется на схожесть с оригиналом,
и слишком вольная правка отбрасывается. Таймкоды возвращаются словам
выравниванием последовательностей, поэтому синхронность не теряется.
"""

from __future__ import annotations

import json
import os
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable

from correct_text import Edit, _norm, _split_token

BATCH = 25                  # предложений за один запрос
MIN_SIMILARITY = 0.60       # ниже — считаем, что модель перефразировала, и откатываем
MAX_GROWTH = 1.35           # и не даём тексту разрастись

SYSTEM_PROMPT = """Ты редактор русских субтитров для видеокурса по маникюру.

Тебе дают массив фраз, распознанных из речи. Верни массив ИСПРАВЛЕННЫХ фраз —
ровно столько же элементов, в том же порядке.

Правь ТОЛЬКО:
- ошибки распознавания речи (слово заменено похожим по звучанию и не подходит по смыслу);
- профессиональную терминологию маникюра (гель-лак, база, топ, праймер, бондер,
  дегидратор, кутикула, апекс, поталь, фольга, втирка, шиммер, пигмент, слайдеры,
  стемпинг, скрайбер, аппликатор, камуфлирующая база, френч, дисперсионный слой);
- пунктуацию и заглавные буквы;
- слова-паразиты, если они не несут смысла: «ну», «вот», «как бы», «значит»,
  «короче», «это самое», «получается» в роли связки.

ЗАПРЕЩЕНО:
- менять порядок слов;
- перефразировать, сокращать или дополнять мысль;
- добавлять факты, которых нет во фразе;
- объединять или разделять фразы.

Если фраза уже верна — верни её без изменений. Отвечай только JSON-массивом строк."""


# ------------------------------------------------------------------ провайдеры

def _gemini(prompt: str, payload: list[str]) -> list[str] | None:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model="gemini-3-flash",
        contents=json.dumps(payload, ensure_ascii=False),
        config=types.GenerateContentConfig(
            system_instruction=prompt,
            temperature=0.0,
            response_mime_type="application/json",
        ),
    )
    return _parse_array(response.text, len(payload))


def _openai(prompt: str, payload: list[str]) -> list[str] | None:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    from openai import OpenAI

    client = OpenAI(api_key=key)
    response = client.chat.completions.create(
        model="gpt-5.4-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        response_format={"type": "json_object"},
    )
    return _parse_array(response.choices[0].message.content or "", len(payload))


PROVIDERS: dict[str, Callable[[str, list[str]], list[str] | None]] = {
    "gemini": _gemini,
    "openai": _openai,
}


def _parse_array(text: str, expected: int) -> list[str] | None:
    """Достать массив строк из ответа, даже если модель завернула его в объект."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if match:
        text = match.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                data = value
                break
    if not isinstance(data, list) or len(data) != expected:
        return None
    return [str(item) for item in data]


# ------------------------------------------------------- выравнивание таймкодов

def realign(old_words: list[dict], new_text: str) -> list[dict]:
    """
    Вернуть словам исправленной фразы время исходных.

    Совпавшие слова сохраняют свои таймкоды; вставленные и заменённые получают
    время пропорционально длине в промежутке между ближайшими совпадениями.
    """
    new_tokens = new_text.split()
    if not new_tokens:
        return []
    if not old_words:
        return []

    old_keys = [_norm(_split_token(w["w"])[1]) for w in old_words]
    new_keys = [_norm(_split_token(t)[1]) for t in new_tokens]

    slots: list[dict | None] = [None] * len(new_tokens)
    for tag, i1, i2, j1, j2 in SequenceMatcher(a=old_keys, b=new_keys).get_opcodes():
        if tag != "equal":
            continue
        for k in range(j2 - j1):
            src = old_words[i1 + k]
            slots[j1 + k] = {"w": new_tokens[j1 + k], "start": src["start"],
                             "end": src["end"], "prob": src.get("prob", 1.0)}

    sentence_start = old_words[0]["start"]
    sentence_end = old_words[-1]["end"]
    index = 0
    while index < len(slots):
        if slots[index] is not None:
            index += 1
            continue
        run_end = index
        while run_end < len(slots) and slots[run_end] is None:
            run_end += 1
        chunk = new_tokens[index:run_end]
        previous = slots[index - 1] if index else None
        left = previous["end"] if previous else sentence_start
        right = slots[run_end]["start"] if run_end < len(slots) else sentence_end
        if right <= left:
            # Слова вставлены между соседними анкерами вплотную. Свободного
            # места нет — занимаем его у предыдущего слова, а не заезжаем на
            # следующее: наезд реплик заметнее сдвинутой на кадр границы.
            need = 0.06 * len(chunk)
            if previous is not None:
                left = max(previous["start"] + 0.02, right - need)
                previous["end"] = round(left, 3)
            else:
                left = max(0.0, right - need)
        total = sum(max(len(t), 1) for t in chunk)
        cursor = left
        for offset, token in enumerate(chunk):
            share = (right - left) * max(len(token), 1) / total
            end = right if offset == len(chunk) - 1 else cursor + share
            slots[index + offset] = {"w": token, "start": round(cursor, 3),
                                     "end": round(end, 3), "prob": 0.9}
            cursor = end
        index = run_end
    return [slot for slot in slots if slot]


# ------------------------------------------------------------------ основной ход

def _sentences(words: list[dict], splitter: Callable[[list[dict]], list[list[dict]]]
               ) -> list[list[dict]]:
    return [s for s in splitter(words) if s]


def polish(words: list[dict], provider: str, *, splitter: Callable, log=print
           ) -> tuple[list[dict], list[Edit]]:
    """Прогнать текст через модель и вернуть слова с восстановленными таймкодами."""
    call = PROVIDERS.get(provider)
    if call is None:
        return words, []

    groups = _sentences(words, splitter)
    originals = [" ".join(w["w"] for w in g) for g in groups]

    fixed: list[str | None] = [None] * len(originals)
    for start in range(0, len(originals), BATCH):
        chunk = originals[start:start + BATCH]
        try:
            answer = call(SYSTEM_PROMPT, chunk)
        except Exception as exc:
            log(f"    {provider}: запрос не прошёл ({type(exc).__name__}: {exc}), "
                "оставляю текст как есть")
            answer = None
        if answer is None:
            continue
        for offset, value in enumerate(answer):
            fixed[start + offset] = value

    out: list[dict] = []
    edits: list[Edit] = []
    rejected = 0
    for i, group in enumerate(groups):
        candidate = (fixed[i] or "").strip()
        original = originals[i]
        if not candidate or candidate == original:
            out.extend(group)
            continue
        ratio = SequenceMatcher(a=_norm(original), b=_norm(candidate)).ratio()
        grew = len(candidate) / max(len(original), 1)
        if ratio < MIN_SIMILARITY or grew > MAX_GROWTH:
            rejected += 1
            out.extend(group)
            continue
        realigned = realign(group, candidate)
        if not realigned:
            out.extend(group)
            continue
        out.extend(realigned)
        edits.append(Edit("llm", original, candidate, i, round(ratio, 3)))

    if rejected:
        log(f"    отклонено правок как слишком вольных: {rejected}")
    return out, edits


def load_env(repo_root: Path) -> None:
    """Ключи лежат в корневом .env — тот же файл, что читает backend."""
    env_file = repo_root / ".env"
    if not env_file.is_file():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file, override=False)
    except ImportError:
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
