"""
Самопроверка модуля без обращения к видео и сети.

    .venv/Scripts/python.exe selftest.py

Проверяет инварианты, на которых держится качество субтитров: перенос строк,
неприкосновенность настоящих русских слов, возврат таймкодов после правки текста
и точность round-trip через .srt.
"""

from __future__ import annotations

import sys

import build_ass
import correct_text
import llm_polish
import segment_cues

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "ok" if condition else "СБОЙ"
    print(f"  {status:5s} {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


# ------------------------------------------------------------------ перенос строк

def test_layout() -> None:
    print("перенос строк")
    samples = [
        "Давайте сегодня рассмотрим с вами такой материал",
        "чтобы у нас не было четкого стыка, а все-таки",
        "и с помощью аппликатора я наношу пигменты",
        "Что касается перекрытия дизайна, то я закрепляю",
        "как пигменты.",
    ]
    for text in samples:
        lines, ok = segment_cues.layout_lines_checked(text)
        short = text[:32] + ("…" if len(text) > 32 else "")
        check(f"уложилось: {short}", ok)
        check("не длиннее лимита", all(len(x) <= segment_cues.MAX_CHARS_PER_LINE for x in lines),
              str([len(x) for x in lines]))
        check("не более двух строк", len(lines) <= segment_cues.MAX_LINES)
        check("слова не разорваны", " ".join(lines) == " ".join(text.split()))
        if len(lines) > 1:
            tail = segment_cues._bare(lines[0].split()[-1])
            check("строка не кончается служебным словом",
                  tail not in segment_cues.NO_LINE_END, tail)

    # Текст, который в две строки по лимиту не влезает, должен честно сказать
    # «не уложился» — по этому признаку сборщик дробит отрезок дальше, а не
    # рвёт строку посреди слова.
    too_long = ("Давайте сегодня рассмотрим с вами такой замечательный материал, "
                "как пигменты, я их просто обожаю")
    _, ok = segment_cues.layout_lines_checked(too_long)
    check("слишком длинный текст помечен как неукладываемый", not ok)


# ------------------------------------------------------------------ правка текста

def test_corrections() -> None:
    print("правка терминов")
    vocab = correct_text.build_vocabulary(correct_text.load_glossary())

    protected = ["покрываем", "сразу", "прозрачный", "просушили", "второй",
                 "пример", "кисточки", "блесточки", "пользоваться", "остальное"]
    for word in protected:
        fixed, _ = correct_text.fix_text(word, vocab)
        check(f"настоящее слово не тронуто: {word}", fixed == word, fixed)

    broken = {
        "фальгу": "фольгу", "фолька": "фольга", "галографическая": "голографическая",
        "полемеризоваться": "полимеризоваться", "пидментированный": "пигментированный",
        "бюрзворсовой": "безворсовой", "фаренч": "френч",
    }
    for word, expected in broken.items():
        fixed, edits = correct_text.fix_text(word, vocab)
        check(f"искажение исправлено: {word} → {expected}", fixed == expected, fixed)

    words = [{"w": "гель", "start": 1.0, "end": 1.3, "prob": 1.0},
             {"w": "лака,", "start": 1.3, "end": 1.8, "prob": 1.0}]
    fixed, _ = correct_text.correct_words(words)
    check("«гель лака» склеено в «гель-лака»",
          " ".join(w["w"] for w in fixed).startswith("гель-лака"),
          " ".join(w["w"] for w in fixed))

    glued = [{"w": "все", "start": 1.0, "end": 1.2, "prob": 1.0},
             {"w": "-таки", "start": 1.2, "end": 1.5, "prob": 1.0}]
    fixed, _ = correct_text.correct_words(glued)
    check("дефисный хвост приклеен без пробела",
          fixed[0]["w"] == "все-таки", fixed[0]["w"])


# ------------------------------------------------------------- возврат таймкодов

def test_realign() -> None:
    print("возврат таймкодов после правки текста")
    old = [
        {"w": "которую", "start": 10.0, "end": 10.4, "prob": 0.9},
        {"w": "мы", "start": 10.4, "end": 10.6, "prob": 0.9},
        {"w": "для", "start": 10.6, "end": 10.8, "prob": 0.9},
        {"w": "себя", "start": 10.8, "end": 11.1, "prob": 0.9},
        {"w": "придерели.", "start": 11.1, "end": 11.9, "prob": 0.46},
    ]
    cases = {
        "замена слова": "которую мы для себя определили.",
        "удаление слова": "которую для себя определили.",
        "вставка слова": "которую мы с вами для себя определили.",
        "вставка в начале": "вот которую мы для себя определили.",
        "без изменений": "которую мы для себя придерели.",
    }
    for name, text in cases.items():
        out = llm_polish.realign(old, text)
        ordered = all(out[i]["start"] < out[i]["end"] <= out[i + 1]["start"] + 1e-9
                      for i in range(len(out) - 1))
        check(f"{name}: реплики не наезжают", ordered and out[-1]["start"] < out[-1]["end"])
        check(f"{name}: не вышли за границы фразы",
              out[0]["start"] >= -1e-6 and out[-1]["end"] <= old[-1]["end"] + 1e-6)
        check(f"{name}: число слов совпало с текстом", len(out) == len(text.split()))


# ------------------------------------------------------------------ round-trip srt

def test_srt_roundtrip() -> None:
    print("round-trip через .srt")
    cues = [
        segment_cues.Cue(1.0, 3.2, ["Давайте сегодня рассмотрим",
                                    "с вами такой замечательный материал,"]),
        segment_cues.Cue(3.4, 4.6, ["как пигменты."]),
    ]
    text = build_ass.build_srt(cues)
    back = build_ass.parse_srt(text)
    check("число реплик сохранилось", len(back) == len(cues))
    check("текст сохранился", all(a.text == b.text for a, b in zip(back, cues)))
    check("таймкоды сохранились",
          all(abs(a.start - b.start) < 0.002 and abs(a.end - b.end) < 0.002
              for a, b in zip(back, cues)))

    merged = text.replace("Давайте сегодня рассмотрим\nс вами такой замечательный материал,",
                          "Давайте сегодня рассмотрим с вами такой замечательный материал,")
    rewrapped = build_ass.parse_srt(merged)
    check("склеенная руками строка переразбита обратно",
          len(rewrapped[0].lines) == 2
          and all(len(x) <= segment_cues.MAX_CHARS_PER_LINE for x in rewrapped[0].lines))


# ------------------------------------------------------------------------ караоке

def test_karaoke() -> None:
    print("караоке-теги")
    import re

    words = [
        {"w": "Давайте", "start": 0.73, "end": 1.15, "prob": 0.9},
        {"w": "сегодня", "start": 1.15, "end": 1.59, "prob": 0.9},
        {"w": "рассмотрим", "start": 1.70, "end": 2.45, "prob": 0.9},
        {"w": "материал,", "start": 2.45, "end": 3.10, "prob": 0.9},
    ]
    cue = segment_cues.Cue(0.264, 3.40,
                           ["Давайте сегодня", "рассмотрим материал,"], words)
    text = build_ass.karaoke_text(cue)
    check("теги собрались", text is not None)
    if not text:
        return

    tags = [int(x) for x in re.findall(r"\\k[f]?(\d+)", text)]
    total = sum(tags) / 100
    check("сумма тегов не превышает длительность реплики",
          total <= cue.duration + 0.01, f"{total:.2f} против {cue.duration:.2f}")

    # Заезд до первого слова обязан быть вынесен в пустой тег, иначе заливка
    # стартует раньше голоса.
    lead = int(round((words[0]["start"] - cue.start) * 100))
    check("зазор до первого слова компенсирован",
          text.startswith("{" + chr(92) + "k" + str(lead) + "}"), text[:16])

    # Пауза между словами тоже должна быть отдельным тегом.
    check("пауза между словами вынесена в тег", text.count(chr(92) + "k") >= 2)

    visible = re.sub(r"\{[^}]*\}", "", text).replace("\\N", " ")
    check("видимый текст совпадает с репликой",
          " ".join(visible.split()) == cue.text, visible)
    check("нет лишних пробелов",
          not visible.startswith(" ") and "  " not in visible, repr(visible))

    without = segment_cues.Cue(0.0, 2.0, ["Текст без пословного времени"], [])
    check("без пословного времени реплика остаётся обычной",
          build_ass.karaoke_text(without) is None)

    mismatched = segment_cues.Cue(0.0, 2.0, ["Одно два три"], words)
    check("при несовпадении числа слов караоке не собирается",
          build_ass.karaoke_text(mismatched) is None)


# ------------------------------------------------------------------ сборка реплик

def test_cue_limits() -> None:
    print("лимиты реплик")
    words = []
    t = 0.0
    phrase = ("Давайте сегодня рассмотрим с вами такой замечательный материал как пигменты "
              "я их просто обожаю с ними можно творить невероятное количество интересных "
              "дизайнов для того чтобы делать этот дизайн нам понадобятся сами пигменты").split()
    for i, w in enumerate(phrase):
        words.append({"w": w + ("." if i in (10, 24) else ""),
                      "start": round(t, 3), "end": round(t + 0.32, 3), "prob": 0.9})
        t += 0.36
    cues = segment_cues.build_cues(words)
    check("реплики собраны", len(cues) > 0)
    check("не более двух строк", all(len(c.lines) <= segment_cues.MAX_LINES for c in cues))
    check("строки в пределах лимита",
          all(len(x) <= segment_cues.MAX_CHARS_PER_LINE for c in cues for x in c.lines))
    check("реплики не наезжают",
          all(cues[i].end <= cues[i + 1].start + 1e-6 for i in range(len(cues) - 1)))
    check("длительность не ниже жёсткого пола",
          all(c.duration >= segment_cues.HARD_MIN_DUR - 0.01 for c in cues),
          str(min(c.duration for c in cues)))
    check("текст не потерян",
          " ".join(c.text for c in cues).replace(".", "") == " ".join(w["w"] for w in words).replace(".", ""))


def main() -> int:
    for suite in (test_layout, test_corrections, test_realign,
                  test_srt_roundtrip, test_karaoke, test_cue_limits):
        suite()
        print()
    if FAILURES:
        print(f"СБОЕВ: {len(FAILURES)}")
        for name in FAILURES:
            print(f"  {name}")
        return 1
    print("Все проверки пройдены.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
