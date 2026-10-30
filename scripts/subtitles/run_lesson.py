"""
Пересборка субтитров и цветокор для одного урока.

    python run_lesson.py --lesson pigmenty                # полный прогон
    python run_lesson.py --lesson pigmenty --rerender-subs # после правки .srt

Исходники в video-lessons/ открываются только на чтение; всё новое пишется
в video-lessons-remastered/<slug>/.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import build_ass
import detect_band
import grade as grade_mod
import render as render_mod
import segment_cues
import llm_polish
from correct_text import correct_words, format_report, load_glossary
from paths import (VIDEO_CATALOG, fonts_dir, lesson_dirs, promo_output_dir, remaster_root,
                   repo_root, resolve_lesson)
from transcribe_words import find_audio, transcribe

SCENE_THRESHOLD = 0.35
HAND_FIX_CPS = 25.0        # выше этого живая речь не идёт — след сорвавшегося выравнивания


def log(message: str) -> None:
    print(message, flush=True)


def scene_cuts(video: Path, cache: Path, *, enabled: bool = True) -> list[float]:
    """Монтажные склейки, чтобы титр не переезжал через стык."""
    if not enabled:
        return []
    if cache.is_file():
        return json.loads(cache.read_text(encoding="utf-8"))
    log("  поиск монтажных склеек")
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video),
         "-filter:v", f"select='gt(scene,{SCENE_THRESHOLD})',metadata=print:file=-",
         "-an", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    cuts = sorted({round(float(m), 3) for m in re.findall(r"pts_time:([\d.]+)", out)})
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(cuts), encoding="utf-8")
    return cuts


def old_transcript_stats(slug: str) -> dict | None:
    """Метрики старых субтитров — для колонки «было» в отчёте."""
    path = promo_output_dir(slug) / "transcript.json"
    if not path.is_file():
        return None
    segments = json.loads(path.read_text(encoding="utf-8"))["segments"]
    if not segments:
        return None
    texts = [s["text"] for s in segments]
    lens = sorted(len(t) for t in texts)
    durs = sorted(s["end"] - s["start"] for s in segments)
    cps = sorted(len(s["text"]) / max(s["end"] - s["start"], 1e-3) for s in segments)
    return {
        "cues": len(segments),
        "line_chars_max": max(lens),
        "line_chars_median": lens[len(lens) // 2],
        "cue_chars_max": max(lens),
        "dur_max": round(durs[-1], 2),
        "dur_median": round(durs[len(durs) // 2], 2),
        "cps_max": round(cps[-1], 1),
        "cps_median": round(cps[len(cps) // 2], 1),
        "duplicates": len(texts) - len(set(texts)),
    }


def stats_report(cues: list[segment_cues.Cue], slug: str) -> str:
    new = segment_cues.cue_stats(cues)
    old = old_transcript_stats(slug)
    rows = [
        ("реплик", "cues", None),
        ("символов в строке, медиана", "line_chars_median", segment_cues.MAX_CHARS_PER_LINE),
        ("символов в строке, максимум", "line_chars_max", segment_cues.MAX_CHARS_PER_LINE),
        ("символов в реплике, максимум", "cue_chars_max", segment_cues.MAX_CHARS),
        ("строк в реплике, максимум", "max_lines", segment_cues.MAX_LINES),
        ("длительность, медиана", "dur_median", None),
        ("длительность, максимум", "dur_max", segment_cues.MAX_DUR),
        ("длительность, минимум", "dur_min", None),
        ("скорость чтения, медиана", "cps_median", segment_cues.MAX_CPS),
        ("скорость чтения, максимум", "cps_max", segment_cues.MAX_CPS),
        ("дублей", "duplicates", 0),
    ]
    width = max(len(r[0]) for r in rows) + 2
    lines = [
        f"{'метрика':<{width}}{'было':>10}{'стало':>10}{'норма':>10}",
        "-" * (width + 30),
    ]
    for label, key, limit in rows:
        was = old.get(key, "—") if old else "—"
        now = new.get(key, "—")
        lines.append(f"{label:<{width}}{str(was):>10}{str(now):>10}{str(limit if limit is not None else '—'):>10}")

    problems = segment_cues.check_cues(cues)
    lines.append("")
    if problems:
        lines.append(f"НАРУШЕНИЙ СТАНДАРТА: {len(problems)}")
        lines.extend("  " + p for p in problems[:40])
        if len(problems) > 40:
            lines.append(f"  … и ещё {len(problems) - 40}")
    else:
        lines.append("НАРУШЕНИЙ СТАНДАРТА НЕТ")
    over = [c for c in cues if c.cps > segment_cues.MAX_CPS]
    if over:
        lines.append("")
        lines.append(
            f"Реплик быстрее {segment_cues.MAX_CPS:.0f} симв/с: {len(over)} из {len(cues)} "
            f"({len(over) / len(cues):.0%}), максимум {max(c.cps for c in over):.1f}. "
            "Это темп речи, а не разбивка: свободных пауз рядом нет, "
            "растягивать реплику дальше — значит разойтись со звуком."
        )

    # Скорость выше HAND_FIX_CPS для живой речи недостижима. Такие места — след
    # сорвавшегося выравнивания Whisper: подряд идущие слова получают один
    # таймкод, и текст там обычно тоже подпорчен повтором. Автоматически время
    # не сочинить, поэтому выносим их списком — по таймкоду легко найти в .srt.
    hand = [c for c in cues if c.cps > HAND_FIX_CPS]
    if hand:
        lines.append("")
        lines.append(f"РЕПЛИКИ ПОД РУЧНУЮ ПРАВКУ ({len(hand)}) — ищите по таймкоду в .srt:")
        for cue in sorted(hand, key=lambda c: -c.cps):
            lines.append(f"  {_srt_stamp(cue.start)}  {cue.duration:4.2f} с  "
                         f"{cue.cps:5.1f} симв/с  {cue.text}")
    return "\n".join(lines) + "\n"


def _srt_stamp(seconds: float) -> str:
    h, rem = divmod(max(0.0, seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def build_subtitle_cues(slug: str, dirs: dict[str, Path], video: Path,
                        *, use_cuts: bool, force_asr: bool,
                        corrector: str = "none") -> tuple[list[segment_cues.Cue], str]:
    audio = find_audio(slug, video, dirs["work"])
    data = transcribe(
        audio,
        dirs["subs"] / f"{slug}.words.json",
        initial_prompt=load_glossary().get("prompt_terms", ""),
        force=force_asr,
    )
    log(f"  распознано слов: {len(data['words'])}")

    words, edits = correct_words(data["words"])
    if corrector != "none":
        llm_polish.load_env(repo_root())
        log(f"  правка текста моделью ({corrector})")
        words, llm_edits = llm_polish.polish(
            words, corrector, splitter=segment_cues.split_sentences, log=log)
        edits += llm_edits
    report = format_report(edits)
    (dirs["qa"] / "corrections.diff.txt").parent.mkdir(parents=True, exist_ok=True)
    (dirs["qa"] / "corrections.diff.txt").write_text(report, encoding="utf-8")
    log(f"  правок текста: {len(edits)}")

    cuts = scene_cuts(video, dirs["work"] / "cuts.json", enabled=use_cuts)
    if cuts:
        log(f"  монтажных склеек: {len(cuts)}")
    cues = segment_cues.build_cues(words, cuts)
    log(f"  реплик собрано: {len(cues)}")
    return cues, report


def write_all_subtitles(cues: list[segment_cues.Cue], slug: str, dirs: dict[str, Path],
                        band: dict, *, write_srt: bool = True,
                        karaoke: str | None = None) -> dict[str, Path]:
    margin = build_ass.margin_v(band["top"], band["bottom"], band["height"])
    written = build_ass.write_subtitles(
        cues, dirs["subs"], slug,
        width=band["width"], height=band["height"], margin_bottom=margin,
        write_srt=write_srt, karaoke=karaoke,
    )
    (dirs["subs"] / f"{slug}.cues.json").write_text(
        json.dumps([{"start": c.start, "end": c.end, "lines": c.lines} for c in cues],
                   ensure_ascii=False, indent=1),
        encoding="utf-8")
    return written


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Пересобрать субтитры и цветокор для урока")
    ap.add_argument("--lesson", help="slug урока, например pigmenty")
    ap.add_argument("--all", action="store_true",
                    help="прогнать все уроки курса по порядку, пропуская готовые")
    ap.add_argument("--redo", action="store_true",
                    help="с --all: пересобирать и уже готовые уроки")
    ap.add_argument("--rerender-subs", action="store_true",
                    help="только перерисовать субтитры из отредактированного .srt")
    ap.add_argument("--keep-ass", action="store_true",
                    help="не пересобирать .ass из .srt (для ручной стилевой правки)")
    ap.add_argument("--karaoke", choices=["none", "soft", "brand"], default="none",
                    help="подсветка по словам: soft — белая протяжка, brand — розовая")
    ap.add_argument("--encoder", choices=["x264", "nvenc"], default="x264")
    ap.add_argument("--grade-strength", type=float, default=1.0)
    ap.add_argument("--no-cuts", action="store_true", help="не искать монтажные склейки")
    ap.add_argument("--corrector", choices=["none", "gemini", "openai"], default="none",
                    help="правка текста моделью поверх глоссария (нужен ключ в корневом .env)")
    ap.add_argument("--subs-only", action="store_true",
                    help="остановиться после сборки субтитров, не кодировать видео")
    ap.add_argument("--force-asr", action="store_true", help="распознать заново")
    ap.add_argument("--force-master", action="store_true",
                    help="пересобрать мастер (цветокор и плашку) заново")
    ap.add_argument("--sample", type=float, default=0.0,
                    help="собрать только первые N секунд (быстрая проба)")
    return ap


def run_one(args: argparse.Namespace, slug: str) -> int:
    started = time.time()
    video, title = resolve_lesson(slug)
    dirs = lesson_dirs(slug)
    for key in ("base", "subs", "qa", "work"):
        dirs[key].mkdir(parents=True, exist_ok=True)

    final_path = dirs["base"] / video.name
    master_path = dirs["base"] / f"{video.stem}.master.mp4"
    ass_path = dirs["subs"] / f"{slug}.ass"
    srt_path = dirs["subs"] / f"{slug}.srt"
    band_path = dirs["work"] / "band.json"

    log(f"=== {title} ({video.name}) ===")

    # ---------------------------------------------------------- быстрый цикл
    if args.rerender_subs:
        if not master_path.is_file():
            log("Мастера нет — сначала выполните полный прогон без --rerender-subs")
            return 1
        if not srt_path.is_file():
            log(f"Не найден {srt_path}")
            return 1
        band = json.loads(band_path.read_text(encoding="utf-8"))
        if not args.keep_ass:
            cues = build_ass.parse_srt(srt_path.read_text(encoding="utf-8"))
            log(f"  прочитано реплик из .srt: {len(cues)}")
            if args.karaoke != "none":
                words_path = dirs["subs"] / f"{slug}.words.json"
                if not words_path.is_file():
                    log("  нет пословных таймкодов — караоке пропущено")
                else:
                    source = json.loads(words_path.read_text(encoding="utf-8"))["words"]
                    build_ass.attach_words(cues, source)
                    matched = sum(1 for c in cues if c.words)
                    log(f"  пословное время восстановлено для реплик: {matched}/{len(cues)}")
            write_all_subtitles(cues, slug, dirs, band, write_srt=False,
                                karaoke=None if args.karaoke == "none" else args.karaoke)
            (dirs["qa"] / "cue-stats.txt").write_text(
                stats_report(cues, slug), encoding="utf-8")
        render_mod.burn_subtitles(master_path, ass_path, fonts_dir(), final_path,
                                  enc=args.encoder)
        log(f"Готово за {time.time() - started:.0f} с: {final_path}")
        return 0

    # ------------------------------------------------------------ полный прогон
    if band_path.is_file():
        band = json.loads(band_path.read_text(encoding="utf-8"))
    else:
        log("  поиск полосы старых титров")
        band = detect_band.detect(video, band_path).__dict__
    log(f"  полоса y={band['top']}..{band['bottom']} ({band['bottom'] - band['top']} px), "
        f"текст в {band['frames_with_text']:.0%} кадров")
    detect_band.make_qa_image(video, detect_band.Band(**band), dirs["qa"] / "band-detect.png")

    cues, _ = build_subtitle_cues(slug, dirs, video,
                                  use_cuts=not args.no_cuts, force_asr=args.force_asr,
                                  corrector=args.corrector)
    write_all_subtitles(cues, slug, dirs, band,
                        karaoke=None if args.karaoke == "none" else args.karaoke)
    report = stats_report(cues, slug)
    (dirs["qa"] / "cue-stats.txt").write_text(report, encoding="utf-8")
    log("\n" + report)

    if args.subs_only:
        log(f"Субтитры собраны за {time.time() - started:.0f} с: {srt_path}")
        return 0

    grade_json = dirs["work"] / "grade.json"
    if grade_json.is_file():
        saved = json.loads(grade_json.read_text(encoding="utf-8"))
        chain = saved["chain"]
    else:
        log("  замер картинки для цветокора")
        params = grade_mod.analyse(video, grade_json, strength=args.grade_strength)
        chain = grade_mod.filter_chain(params, strength=args.grade_strength)
    grade_mod.compare_stills(video, chain, dirs["qa"] / "grade-ab.png")

    if master_path.is_file() and not args.force_master and not args.sample:
        log(f"  мастер уже собран, переиспользую ({master_path.stat().st_size / 1e6:.0f} МБ)")
    else:
        render_mod.render_master(video, band, chain, master_path, dirs["work"],
                                 enc=args.encoder, duration=args.sample or None)
    render_mod.burn_subtitles(master_path, ass_path, fonts_dir(), final_path,
                              enc=args.encoder)

    mid = min(len(cues) - 1, len(cues) // 2)
    render_mod.preview(master_path, ass_path, fonts_dir(), dirs["qa"] / "preview-60s.mp4",
                       start=max(0.0, cues[mid].start - 2))
    two_line = [c.start + 0.4 for c in cues if len(c.lines) == 2][:2]
    one_line = [c.start + 0.4 for c in cues if len(c.lines) == 1][:2]
    gaps = _silent_moments(cues)[:2]
    render_mod.stills(final_path, two_line + one_line + gaps, dirs["qa"] / "final-stills.png")

    src = render_mod.probe(video)
    dst = render_mod.probe(final_path)
    (dirs["base"] / "render.json").write_text(json.dumps({
        "lesson": slug, "title": title, "source": str(video),
        "band": band, "grade_chain": chain, "encoder": args.encoder,
        "cues": len(cues), "source_probe": src, "result_probe": dst,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    log("")
    log(f"исходник:  {src['width']}x{src['height']}  {src['duration']:.1f} с  "
        f"{src['size_bytes'] / 1e6:.0f} МБ  аудио {src['audio_codec']}/{src['audio_frames']}")
    log(f"результат: {dst['width']}x{dst['height']}  {dst['duration']:.1f} с  "
        f"{dst['size_bytes'] / 1e6:.0f} МБ  аудио {dst['audio_codec']}/{dst['audio_frames']}")
    log(f"Готово за {(time.time() - started) / 60:.1f} мин: {final_path}")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    if not args.all and not args.lesson:
        log("Укажите --lesson <slug> или --all")
        return 1
    if not args.all:
        return run_one(args, args.lesson)

    slugs = [e.slug for e in VIDEO_CATALOG]
    results: list[tuple[str, str, float]] = []
    batch_started = time.time()
    stop_flag = remaster_root() / "STOP"
    if stop_flag.is_file():
        stop_flag.unlink()
    log(f"Остановить после текущего урока: создайте файл {stop_flag}")

    for position, slug in enumerate(slugs, 1):
        # Проверяем между уроками, а не во время: прерывать кодирование на
        # середине нельзя — останется обрезанный mp4, который на следующем
        # запуске примут за готовый.
        if stop_flag.is_file():
            log("")
            log("Найден файл STOP — останавливаюсь на границе урока")
            stop_flag.unlink()
            for rest in slugs[position - 1:]:
                results.append((rest, "не начат", 0.0))
            break
        video, title = resolve_lesson(slug)
        dirs = lesson_dirs(slug)
        done = ((dirs["subs"] / f"{slug}.srt").is_file() if args.subs_only
                else (dirs["base"] / video.name).is_file())
        if done and not args.redo:
            log(f"[{position}/{len(slugs)}] {title} — уже собран, пропускаю")
            results.append((slug, "пропущен", 0.0))
            continue
        log("")
        log(f"[{position}/{len(slugs)}] {title}")
        started = time.time()
        try:
            code = run_one(args, slug)
            status = "готов" if code == 0 else f"ошибка (код {code})"
        except Exception as exc:
            status = f"ошибка: {type(exc).__name__}: {exc}"
            log(f"  СБОЙ: {status}")
        results.append((slug, status, time.time() - started))

    log("")
    log("=" * 58)
    log(f"{'урок':<14}{'статус':<28}{'минут':>8}")
    for slug, status, spent in results:
        log(f"{slug:<14}{status:<28}{spent / 60:>8.1f}")
    log("")
    log(f"всего: {(time.time() - batch_started) / 60:.0f} мин")
    failed = [s for s, st, _ in results if st.startswith("ошибка")]
    if failed:
        log(f"не собрались: {', '.join(failed)}")
        return 1
    return 0


def _silent_moments(cues: list[segment_cues.Cue]) -> list[float]:
    """Моменты без субтитров — посмотреть, как плашка выглядит пустой."""
    out = []
    for i in range(len(cues) - 1):
        gap = cues[i + 1].start - cues[i].end
        if gap > 1.5:
            out.append(cues[i].end + gap / 2)
    return out


if __name__ == "__main__":
    sys.exit(main())
