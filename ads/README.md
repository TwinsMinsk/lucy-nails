# Reels для курса Nail Design PRO

Ролики 9:16 из уроков курса и фото работ. Тексты, кадры и голос собираются в HyperFrames-композицию
и рендерятся в MP4. Кампании:

- `campaign/` — «За дизайн доплачивают», R1–R10: польза из уроков (ошибки, лайфхаки) и продажа.
- `campaign-vremya-rasti/` — «Время расти», R11–R16: мотивация без секретов уроков («хочешь зарабатывать
  больше», «расти»), на «ты». Сделана 31.10.2026 по просьбе Люси: первая кампания раскрывает суть уроков.

Каждая кампания — папка `ads/campaign*` с теми же файлами (`scripts.md`, `captions.md`, `calendar.md`,
`about.md`, `admin.json`, `reels/`). Номера роликов сквозные, поэтому скрипты находят кампанию по коду ролика
(`tts.py r12`, `build_reel.py r12`); группы роликов и ролики с вариантами хуков задаются в `admin.json`.
Ниже примеры для первой кампании; код пайплайна (`publish.py`, `build_page.py`) лежит в `campaign/`.

- Сценарии и тексты озвучки: [`campaign/scripts.md`](campaign/scripts.md) (единственный источник текста)
- Суфлёр для записи: [`campaign/teleprompter.html`](campaign/teleprompter.html), опубликован как Artifact
- Кадры ролика: `campaign/shots/<reel>.json`; что играет под какими словами: `campaign/reels/<reel>.json`
- Кадр в `reels/<reel>.json` — клип из урока (`"clip"`; `"r03/s01-tear"` берёт клип другого ролика), фото работы
  (`"photo": "folga/folga-14"` из `frontend/public/works`), сетка фото (`"grid": true`: пронумерованные фото или
  список `"grid"` ролика) или графическая карточка (`"card": "modules" | "tariffs" | "calc"`, R9, R10).
  Фото с `"count"` и `"name"` получают счётчик 01…11 вместо субтитров (R1); `"min_shot"` и `"captions_skip_lines"`
  задаются на весь ролик.
- К любому кадру: `"stats"` — крупные цифры поверх окна (R8, R10), `"tone": "mono"` — обесцветить (R8),
  `"frame": "phone"` — клип на экране телефона (R9). На весь ролик: `"scheme"` — схема в углу окна, которая
  рисуется под слова (R6). Финал (`"end"`) — клип или фото.
- Фото `works/folga/folga-07` и `folga-10` подписаны другими мастерами («Мастер … LS Studio») — в рекламу не брать.

## Старые субтитры

В уроках субтитры вшиты в картинку. Их полоса замерена в `video-lessons-remastered/<slug>/.work/band.json`.
`mining/prep_clips.py` режет кадр только выше полосы или, если кадр нужен целиком, только там, где
покадровая проверка (`mining/subs_map.py`) не нашла текста; иначе отказывается.

## Окружение (один раз)

Пайплайн опирается на `scripts/subtitles/` (словные таймкоды Whisper, шрифт для листов) и на замеры полосы
субтитров в `video-lessons-remastered/<slug>/.work/band.json`. На 31.10.2026 `scripts/subtitles/` живёт в ветке
`oleg/subtitles-pipeline` и ещё не влит в `master`. Сами уроки и нарезанные из них клипы в git не попадают:
репозиторий публичный, а уроки — платный курс.

```powershell
uv venv ads/.venv --python 3.12
uv pip install --python ads/.venv/Scripts/python.exe faster-whisper nvidia-cublas-cu12 "nvidia-cudnn-cu12>=9,<10" librosa soundfile numpy pillow auto-editor
```

Сторонние инструменты в `vendor/` (не в git): Real-ESRGAN ncnn-vulkan, [opus-sound-layer](https://github.com/Bodila51/opus-sound-layer) (`uv run scripts/sfx.py kit`).

## Ролик от начала до конца (пример R3)

```powershell
$py = "ads/.venv/Scripts/python.exe"
& $py ads/mining/subs_map.py folga                         # где на экране старые субтитры
& $py ads/mining/contact_sheets.py folga --every 15        # раскадровка урока для выбора кадров
& $py ads/mining/prep_clips.py r03 --preview               # проверить кадрирование
& $py ads/mining/prep_clips.py r03                         # нарезать клипы
& $py ads/audio/prep_vo.py r03 ads/vo/r03-take1.wav        # голос Люси: чистка + тайминги слов
& $py ads/video/build_reel.py r03                          # композиция -> ads/video/index.html
cd ads/video; npx hyperframes@0.8.221 check .; npx hyperframes@0.8.221 render . -o ../out/r03/r03-raw.mp4 -q delivery -f 30
& $py ads/video/finish.py r03 ads/out/r03/r03-raw.mp4 --name r03   # -14 LUFS, обложка, лист для проверки
```

Пока записи нет, `audio/tts_placeholder.ps1 -Reel r03` даёт черновой голос Windows, а `prep_vo.py ... --draft`
размечает его. После записи достаточно повторить `prep_vo.py`, `build_reel.py`, рендер и `finish.py`:
склейки, подписи и субтитры привязаны к словам и пересчитаются сами.

Голос нейросетью: `audio/tts.py` через OpenRouter (ключ в переменной пользователя `OPENROUTER_API_KEY`).
`tts.py r08 --samples --check` озвучивает ролик всеми голосами из `SAMPLES` в `ads/vo/samples/r08/` и сверяет
прочитанное со сценарием через Whisper; `tts.py r03 --check` пишет `ads/vo/r03-tts.wav` голосом кампании
(Gemini 3.8 Flash TTS «Sulafat», выбран 31.10.2026), дальше `prep_vo.py r03 ads/vo/r03-tts.wav --tts` (без вырезки
пауз) и сборка как обычно.

Музыки в мастере нет: трек добавляется при публикации в Instagram (у бизнес-аккаунта библиотека ограничена).

## Варианты хуков

У R1, R3 и R8 в `reels/<reel>.json` есть `"hooks"`: другой заголовок и, при желании, другой первый кадр;
голос и остальной ролик те же. Сборка варианта: `build_reel.py r03 --hook b`, рендер в
`ads/out/r03/r03-hook-b-raw.mp4`, затем `finish.py r03 ... --name r03-hook-b`. Как их тестировать — в
[`campaign/calendar.md`](campaign/calendar.md).

## Страница для презентации

`python ads/campaign/build_page.py` собирает `ads/out/presentation/index.html`: все ролики с плеером, тексты
озвучки, подписи к постам, хуки, календарь и что нужно от Люси. Текст берётся из `scripts.md`, `captions.md`,
`calendar.md` и `reels/*.json`, видео — облегчённые копии готовых роликов (пересоздаются, если ролик новее).
Страница опубликована как Artifact (https://claude.ai/artifact/Bqs2KEZXPciboMNtezcxuZ, приватная — открывать доступ
через меню Share); после пересборки её публикуют заново по тому же пути.

## Раздел «Реклама» в админке сайта

Основное место для Люси — `https://lucysmirnova.ru/admin/ads` (права `ads.read`/`ads.manage`, роль «marketer» или
owner/admin): ролики с плеером и скачиванием, подписи и ссылки с меткой, суфлёр, другие начала роликов, статус
публикации, загрузка записей голоса, комментарии, календарь, задачи и вкладка «О кампании».

```powershell
$env:ADS_SYNC_TOKEN = "<то же значение, что у Backend в Railway>"   # не коммитить, не печатать
& ads/.venv/Scripts/python.exe ads/campaign/publish.py              # прод; --api http://127.0.0.1:8000/api — локально
& ads/.venv/Scripts/python.exe ads/campaign/publish.py --campaign ads/campaign-vremya-rasti   # другая кампания
```

`publish.py` берёт тексты из тех же источников, что и `build_page.py`, плюс [`campaign/about.md`](campaign/about.md)
(вкладка «О кампании», текст для Люси) и [`campaign/admin.json`](campaign/admin.json) (название, старт, время, задачи).
Файлы — финальный рендер `ads/out/<reel>/<reel>.mp4`, если он есть, иначе черновик; отправляются только изменённые
(по sha256). Статусы, отметки задач, записи и комментарии команды при повторной отправке не затираются. Записи голоса,
загруженные Люсей, скачиваются в `ads/vo/inbox/<reel>/`, комментарии печатаются в консоль.
