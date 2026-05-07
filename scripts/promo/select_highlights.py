"""Выбор фрагментов для промо через LLM или эвристику."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)

OPENAI_HIGHLIGHT_MODEL = os.environ.get("OPENAI_HIGHLIGHT_MODEL", "gpt-5.4-mini")
GEMINI_HIGHLIGHT_MODEL = os.environ.get("GEMINI_HIGHLIGHT_MODEL", "gemini-3-flash")


class HighlightSegment(BaseModel):
    start_sec: float = Field(..., ge=0)
    end_sec: float = Field(..., ge=0)
    reason: str = ""

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end_sec <= self.start_sec:
            raise ValueError("end_sec must be > start_sec")
        return self


class HighlightsPlan(BaseModel):
    title: str = ""
    description: str = ""
    bullets: list[str] = Field(default_factory=list)
    highlights: list[HighlightSegment] = Field(default_factory=list)


def _segments_summary(transcript: dict[str, Any], max_chars: int = 12000) -> str:
    lines: list[str] = []
    for s in transcript.get("segments", []):
        lines.append(f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}")
    text = "\n".join(lines)
    if len(text) > max_chars:
        return text[:max_chars] + "\n…"
    return text


def _parse_json_loose(text: str) -> dict[str, Any]:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("No JSON object in LLM response")
    return json.loads(m.group(0))


def _highlight_prompt(lesson_title: str, duration_cap: float, summary: str) -> str:
    return f"""Ты редактор промо-роликов премиум-курса по дизайну ногтей.

Урок: «{lesson_title}».
Длительность видео (сек): {duration_cap:.1f}.

Ниже транскрипт с таймкодами [start-end].

Задача:
1. Выбери 4–6 непрерывных фрагментов из ОДНОГО и того же видео в хронологическом порядке.
2. Суммарная длительность фрагментов 35–55 секунд (не выходи за границы видео).
3. Каждый фрагмент — законченная мысль, без обрыва фразы (минимум ~4 сек на фрагмент).
4. Сформулируй description: 2–3 предложения о том, что зритель узнает в уроке.
5. bullets: 3–4 коротких пункта «что узнаете» (без воды).

Верни ТОЛЬКО JSON без markdown:
{{
  "title": "кратко на русском",
  "description": "…",
  "bullets": ["…", "…"],
  "highlights": [{{"start_sec": 12.5, "end_sec": 18.2, "reason": "…"}}, …]
}}

Транскрипт:
{summary}
"""


def _call_openai_json(prompt: str) -> str:
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing")

    client = OpenAI(api_key=api_key)
    models_to_try = [OPENAI_HIGHLIGHT_MODEL, "gpt-4o-mini", "gpt-4o"]
    last_err: Exception | None = None
    for model in models_to_try:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            choice = resp.choices[0].message.content
            if not choice:
                raise RuntimeError("Empty OpenAI response")
            logger.info("Highlights: OpenAI model=%s OK", model)
            return choice
        except Exception as e:
            last_err = e
            logger.warning("OpenAI model %s failed: %s", model, e)
            continue
    raise last_err or RuntimeError("OpenAI failed")


def _call_gemini_json(prompt: str) -> str:
    from google import genai
    from google.genai import types

    api_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or ""
    )
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY missing")

    client = genai.Client(api_key=api_key)
    models_to_try = [GEMINI_HIGHLIGHT_MODEL, "gemini-2.5-flash", "gemini-2.0-flash"]
    config = types.GenerateContentConfig(response_mime_type="application/json")
    last_err: Exception | None = None
    for model in models_to_try:
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            text = getattr(resp, "text", None) or ""
            if not text.strip():
                raise RuntimeError("Empty Gemini response")
            logger.info("Highlights: Gemini model=%s OK", model)
            return text
        except Exception as e:
            last_err = e
            logger.warning("Gemini model %s failed: %s", model, e)
            continue
    raise last_err or RuntimeError("Gemini failed")


def _call_anthropic(prompt: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    block = msg.content[0]
    if block.type != "text":
        raise RuntimeError("Unexpected Anthropic response")
    return block.text


def select_highlights_llm(
    lesson_title: str,
    transcript: dict[str, Any],
    duration_cap: float,
) -> HighlightsPlan:
    summary = _segments_summary(transcript)
    prompt = _highlight_prompt(lesson_title, duration_cap, summary)

    if os.environ.get("OPENAI_API_KEY"):
        try:
            raw = _call_openai_json(prompt)
            data = _parse_json_loose(raw)
            return HighlightsPlan.model_validate(data)
        except Exception as e:
            logger.warning("OpenAI highlights failed, trying Gemini: %s", e)

    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        try:
            raw = _call_gemini_json(prompt)
            data = _parse_json_loose(raw)
            return HighlightsPlan.model_validate(data)
        except Exception as e:
            logger.warning("Gemini highlights failed, trying Anthropic: %s", e)

    if os.environ.get("ANTHROPIC_API_KEY"):
        raw = _call_anthropic(prompt)
        data = _parse_json_loose(raw)
        return HighlightsPlan.model_validate(data)

    raise RuntimeError("No LLM API key configured")


def _fallback_even_segments(transcript: dict[str, Any], duration_cap: float) -> HighlightsPlan:
    segs = transcript.get("segments") or []
    if not segs:
        raise ValueError("Пустой транскрипт")

    # Цель ~45 с суммарно, 5 клипов по ~9 с
    target_total = min(48.0, max(35.0, duration_cap * 0.08))
    n_clips = 5
    clip_len = target_total / n_clips

    highlights: list[HighlightSegment] = []
    total = 0.0
    step = max(len(segs) // (n_clips + 1), 1)

    for i in range(n_clips):
        idx = min(i * step, len(segs) - 1)
        s = segs[idx]
        start = float(s["start"])
        end = min(start + clip_len, float(s["end"]) + clip_len * 0.5, duration_cap)
        if end - start < 3.0:
            end = min(start + 4.0, duration_cap)
        if end <= start:
            continue
        highlights.append(HighlightSegment(start_sec=start, end_sec=end, reason="auto"))
        total += end - start
        if total >= target_total:
            break

    title = "Превью урока"
    desc = "Ключевые моменты из урока — техника, материалы и практические советы."
    bullets = [
        "Разбор пошаговых действий",
        "Типичные ошибки и как их избежать",
        "Финишный результат и закрепление",
    ]
    return HighlightsPlan(title=title, description=desc, bullets=bullets, highlights=highlights)


def normalize_highlights(
    plan: HighlightsPlan,
    duration_cap: float,
    *,
    min_seg: float = 3.5,
    max_seg: float = 14.0,
) -> HighlightsPlan:
    """Подрезает сегменты к границам видео и чинит пересечения."""

    fixed: list[HighlightSegment] = []
    for h in plan.highlights:
        start = max(0.0, min(h.start_sec, duration_cap - min_seg))
        end = min(duration_cap, max(h.end_sec, start + min_seg))
        end = min(end, start + max_seg)
        if end - start >= min_seg:
            fixed.append(HighlightSegment(start_sec=start, end_sec=end, reason=h.reason))

    # суммарная длина > 60 — укорачиваем с конца
    total = sum(x.end_sec - x.start_sec for x in fixed)
    while total > 58.0 and fixed:
        last = fixed[-1]
        new_dur = max(min_seg, (last.end_sec - last.start_sec) - (total - 55.0))
        fixed[-1] = HighlightSegment(
            start_sec=last.start_sec,
            end_sec=last.start_sec + new_dur,
            reason=last.reason,
        )
        total = sum(x.end_sec - x.start_sec for x in fixed)

    plan = plan.model_copy(update={"highlights": fixed})
    return plan


def _has_any_llm_key() -> bool:
    return bool(
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
    )


def select_highlights(
    lesson_title: str,
    transcript: dict[str, Any],
    duration_cap: float,
    *,
    prefer_llm: bool = True,
) -> HighlightsPlan:
    cap = float(transcript.get("duration_seconds") or duration_cap)
    cap = min(cap, duration_cap)

    if prefer_llm and _has_any_llm_key():
        try:
            plan = select_highlights_llm(lesson_title, transcript, cap)
        except Exception as e:
            logger.warning("LLM highlights failed, heuristic fallback: %s", e)
            plan = _fallback_even_segments(transcript, cap)
    else:
        plan = _fallback_even_segments(transcript, cap)

    plan = normalize_highlights(plan, cap)
    plan = _ensure_non_empty_highlights(plan, transcript, cap)
    return plan


def _ensure_non_empty_highlights(
    plan: HighlightsPlan,
    transcript: dict[str, Any],
    cap: float,
) -> HighlightsPlan:
    if plan.highlights:
        return plan
    segs = transcript.get("segments") or []
    if not segs:
        return plan
    s = segs[0]
    start = float(s["start"])
    end = min(start + 12.0, cap)
    if end <= start:
        end = min(start + 5.0, cap)
    return plan.model_copy(
        update={
            "highlights": [
                HighlightSegment(start_sec=start, end_sec=end, reason="автовыбор первого фрагмента"),
            ]
        }
    )
