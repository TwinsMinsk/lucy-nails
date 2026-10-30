# scripts/subtitles

**Parent context:** `../AGENTS.md`
**Generated:** 2026-08-26 · **Updated:** 2026-10-30

## Purpose

Офлайн Python-пайплайн, делающий из урока `video-lessons/*.mp4` новую копию в `video-lessons-remastered/<slug>/`: заново распознанные субтитры со словными таймкодами → правка терминологии → сборка реплик по правилам вещательных субтитров → вжигание поверх матовой плашки, скрывающей старые вшитые титры → мягкий beauty-грейд. Исходники открываются **только на чтение**. Работает независимо от backend-venv, своим `requirements.txt` и venv на Python 3.12 (CTranslate2 не собирается под 3.14).

## Key Files

| File | Description |
|------|-------------|
| [`run_lesson.py`](run_lesson.py) | Главный CLI и оркестратор (`--lesson <slug>`). Кеширует каждый шаг в `video-lessons-remastered/<slug>/.work/`; режим `--rerender-subs` перерисовывает субтитры из отредактированного `.srt` без пересчёта грейда и распознавания; `--all` прогоняет весь курс (`--redo` — с пересборкой готовых), `--subs-only` останавливается до кодирования. Прочие флаги: `--keep-ass`, `--karaoke none\|soft\|brand`, `--encoder x264\|nvenc`, `--grade-strength`, `--no-cuts`, `--corrector none\|gemini\|openai`, `--force-asr`, `--force-master`, `--sample N` |
| [`detect_band.py`](detect_band.py) | Измеряет полосу вшитых титров по выборке кадров (яркий пиксель рядом с тёмным = контур текста). Порог — по доле кадров, а не по доле от максимума, иначе редкая вторая строка отсекается. Даёт `band.json` и `qa/band-detect.png` |
| [`transcribe_words.py`](transcribe_words.py) | `faster-whisper` large-v3 с `word_timestamps=True`. Подхватывает готовый `scripts/promo/output/<slug>/audio_16k.wav`. CUDA-DLL регистрируются из колёс `nvidia-*` (namespace-пакет, идти через `__path__`) |
| [`correct_text.py`](correct_text.py) | Два слоя правки: многословные замены («гель лак» → «гель-лак») и нечёткое сопоставление словоформ с глоссарием. Правит **только** слова, неизвестные `pymorphy3`; форма термина ставится по граммемам искажённого слова |
| [`segment_cues.py`](segment_cues.py) | Ядро: предложения → реплики → перенос строк. Лимиты `MAX_CHARS_PER_LINE=38`, `MAX_LINES=2`, `MAX_CPS=17`, `MIN_DUR/MAX_DUR`. Списки предлогов, частиц и союзов, которыми строка не может кончаться |
| [`build_ass.py`](build_ass.py) | `.ass` (Inter Medium 34px, `WrapStyle=2`, `\fad`, `MarginV` из `band.json`) и `.srt`; `parse_srt()` читает отредактированный `.srt` обратно |
| [`grade.py`](grade.py) | Замер `signalstats` + баланс белого по светлым нейтральным пикселям → цепочка фильтров в 10 битах. `qa/grade-ab.png` |
| [`render.py`](render.py) | ffmpeg в два прохода: A — грейд и плашка (`*.master.mp4`), B — вжигание `.ass`. Маски и скрим генерируются Pillow/numpy |
| [`llm_polish.py`](llm_polish.py) | Необязательный второй слой правки текста моделью (Gemini/OpenAI) с возвратом таймкодов через выравнивание последовательностей; правки со схожестью ниже 0.6 отбрасываются |
| [`selftest.py`](selftest.py) | Самопроверка инвариантов без видео и сети |
| [`glossary.json`](glossary.json) | Термины курса: существительные/прилагательные/глаголы, многословные замены, защищённые слова, `prompt_terms` для `initial_prompt` |
| [`paths.py`](paths.py) | Пути пайплайна (`remaster_root`, `lesson_dirs` → `subs/`, `qa/`, `.work/`, `promo_output_dir`, `resolve_lesson`), реэкспорт каталога уроков из `scripts/promo`, принудительный UTF-8 вывод |
| [`requirements.txt`](requirements.txt) | Зависимости только этого пайплайна (`faster-whisper`, `numpy`, `pillow`, `google-genai`, `openai`, `python-dotenv`, `pymorphy3` + словари, `nvidia-cublas-cu12`/`nvidia-cudnn-cu12`) |
| [`fonts/`](fonts/) | `Inter-Medium.ttf` (кириллица полная; используется в `.ass`), `Inter-Regular.ttf`, лицензия `OFL-Inter.txt`. Копия, чтобы не зависеть от worktree сертификатов |
| [`README.md`](README.md) | Инструкция, ключи CLI, разбор тонкостей |

## For AI Agents

### Working In This Directory

- Свой venv: `.venv` на Python 3.12, создаётся `uv venv --python 3.12 .venv`. Backend-venv **не** использовать.
- Карта уроков не дублируется — `find_catalog_entry`/`VIDEO_CATALOG` берутся из [`../promo/catalog.py`](../promo/catalog.py) через [`paths.py`](paths.py), который добавляет корень репозитория в `sys.path`.
- `video-lessons/` и `video-lessons-remastered/` в `.gitignore`; коммитить только код, `glossary.json` и шрифты.
- Пути внутри filtergraph передавать относительными от корня репозитория (`_filter_path`), ffmpeg запускать с `cwd=repo_root()`. Экранирование `F:\` внутри `-vf` ломает парсер.
- Вывод в консоль — UTF-8 принудительно (см. верх [`paths.py`](paths.py)): консоль Windows в cp1251 роняет типографику.

### Грабли, уже наступленные

- **`colorlevels` в ffmpeg 8.1 рушит 10-битный вход** — картинка уходит в чёрное. Точки чёрного/белого и баланс белого сведены в `curves`.
- **`condition_on_previous_text=False` убивает пунктуацию.** В faster-whisper `initial_prompt` действует только на первое окно, дальше модель остаётся без контекста. Петли давятся `repetition_penalty` + `prompt_reset_on_temperature` + `hallucination_silence_threshold`.
- **Нечёткое сопоставление без словарного предохранителя разносит текст** — 39 замен «покрываем» → «перекрываем» на корпусе уроков. Правится только то, чего нет в `pymorphy3`.
- **Дробление реплики не снижает CPS** — делятся и текст, и время. Лечится только растягиванием в паузу.
- **Размывать надо весь кадр, подставляя низ по маске.** Размытие вырезанной полосы даёт несовпадение цвета у кромки — видно линию. Растушёвка идёт выше полосы.
- **Караоке-часы стартуют с начала реплики, а не с первого слова** — зазор и паузы между словами надо выносить в пустые теги `\k`, иначе заливка убегает вперёд голоса (на первой реплике урока — на два слова).
- **Приглушение неспетого текста задавать цветом, а не альфой** — `\fad` управляет альфой всей строки и смазал бы разницу на входе-выходе.
- **Батч останавливать файлом `video-lessons-remastered/STOP`, а не убийством процесса** — прерванный ffmpeg оставляет обрезанный mp4, и следующий запуск примет его за готовый урок.
- `crop` под `yuv420p` молча округляет нечётную высоту вниз — маска перестаёт совпадать с полосой (`alphamerge: sizes do not match`).

### Testing Requirements

Сначала `selftest.py` (быстро, без видео и сети) — проверяет перенос строк, неприкосновенность настоящих слов, возврат таймкодов и round-trip через `.srt`. Дальше — по артефактам в `qa/`:

- `cue-stats.txt` — таблица «было/стало» против старого `transcript.json` и список нарушений стандарта. `check_cues()` должен давать пусто, кроме реплик со скоростью чтения выше 17 симв/с (это темп речи).
- `band-detect.png` — полоса обведена верно на всех кадрах.
- `grade-ab.png`, `final-stills.png`, `preview-60s.mp4` — визуальная приёмка.
- Быстрый прогон: `--sample 90 --no-cuts` (≈2.5 мин) перед полным рендером.
- Остаток старых титров меряется по `*.master.mp4` (он без нового текста), а не по финалу.

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
