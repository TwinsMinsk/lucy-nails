"""Build the campaign overview page (one place to watch every reel and read the plan).

    python ads/campaign/build_page.py      -> ads/out/presentation/index.html and media/ next to it

Text comes from the campaign sources, so the page never drifts from them: hooks and voice-over
from scripts.md, post captions from captions.md, the posting grid from calendar.md, hook variants
from reels/<reel>.json. Media are web-size copies of the rendered reels (720x1280, a few MB each)
and the first seconds of every hook variant, remade only when the render is newer.
"""

from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parent
ADS = CAMPAIGN.parent
OUT = ADS / "out" / "presentation"
sys.path.insert(0, str(ADS / "audio"))
from script import vo_lines  # noqa: E402

REELS = [f"r{n:02d}" for n in range(1, 11)]
LAYERS = [
    ("reach", "Охват", "Вау-визуал, который хочется досмотреть и переслать.", ["r01", "r02"]),
    ("mistakes", "Серия «Ошибка мастера»", "Боль, причина и решение. Такие ролики сохраняют.", ["r03", "r04", "r05", "r06", "r07"]),
    ("sales", "Продажа", "Оффер, ответ на «дорого» и что внутри курса.", ["r08", "r09", "r10"]),
]
HOOK_REELS = ["r01", "r03", "r08"]
TELEPROMPTER = "https://claude.ai/artifact/DumQ6M9FQSLJR2LZAteHfX"
PR_URL = "https://github.com/TwinsMinsk/lucy-nails/pull/31"


def section(text: str, code: str) -> str:
    """The '## R3 ...' section of a campaign markdown file, up to the next heading or rule."""
    m = re.search(rf"^## {code}\b.*?$(.*?)(?=^## |^---$|\Z)", text, re.S | re.M)
    return m.group(0) if m else ""


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         check=True, capture_output=True, text=True).stdout
    return float(out)


def reel_data(reel: str, scripts: str, captions: str) -> dict:
    code = "R" + str(int(reel[1:]))
    sc = section(scripts, code)
    title = re.search(r"«(.+?)»", sc.splitlines()[0]).group(1)
    hook = re.search(r"\*\*Хук на экране:\*\*\s*(.+)", sc).group(1).strip()
    cap = section(captions, code)
    utm = re.search(r"utm_content=([\w-]+)", cap)
    body = "\n".join(cap.splitlines()[1:]).strip()
    spec = json.loads((CAMPAIGN / "reels" / f"{reel}.json").read_text(encoding="utf-8"))
    hooks = [{"id": "a", "lines": [h["text"] for h in spec["headline"]]}]
    hooks += [{"id": k, "lines": [h["text"] for h in v["headline"]]} for k, v in spec.get("hooks", {}).items()]
    final = ADS / "out" / reel / f"{reel}.mp4"
    return {"reel": reel, "code": code, "title": title, "hook": hook, "vo": vo_lines(reel),
            "caption": body, "utm": utm.group(1) if utm else "", "hooks": hooks,
            "seconds": round(duration(final if final.exists() else final.with_name(f"{reel}-draft.mp4")))}


def calendar_rows(text: str) -> list[dict]:
    grid = text.split("## Сетка", 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in grid.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[0].isdigit():
            rows.append({"week": int(cells[0]), "day": cells[1], "what": cells[2], "stories": cells[3]})
    return rows


def md_inline(text: str) -> str:
    """Escape, then keep the two marks the calendar uses: **bold** and `code`."""
    out = html.escape(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", out)


def reel_card(d: dict) -> str:
    vo = "".join(f"<li>{html.escape(line)}</li>" for line in d["vo"])
    return f"""
      <article class="reel" id="{d['reel']}">
        <div class="phone"><video src="media/{d['reel']}.mp4" poster="media/{d['reel']}.jpg" controls playsinline preload="none"></video></div>
        <div class="reel-meta">
          <div class="reel-top"><span class="code">{d['code']}</span><span class="secs">{d['seconds']} с</span></div>
          <h3>{html.escape(d['title'])}</h3>
          <p class="hook">{html.escape(d['hook'])}</p>
          <details><summary>Текст озвучки</summary><ol class="vo">{vo}</ol></details>
          <details><summary>Подпись к посту</summary>
            <pre class="caption" id="cap-{d['reel']}">{html.escape(d['caption'])}</pre>
            <div class="caption-foot"><button type="button" class="copy" data-target="cap-{d['reel']}">Скопировать подпись</button>
            <span class="utm">метка <code>{html.escape(d['utm'])}</code></span></div>
          </details>
        </div>
      </article>"""


def hook_block(d: dict) -> str:
    cells = []
    for h in d["hooks"]:
        lines = "<br>".join(html.escape(x) for x in h["lines"])
        cells.append(f"""
          <figure class="hook-cell">
            <div class="phone small"><video src="media/{d['reel']}-hook-{h['id']}.mp4" muted loop autoplay playsinline preload="auto"></video></div>
            <figcaption><span class="variant">{h['id'].upper()}</span><span>{lines}</span></figcaption>
          </figure>""")
    return f"""
      <div class="hook-row">
        <h3>{d['code']} · {html.escape(d['title'])}</h3>
        <div class="hook-cells">{''.join(cells)}</div>
      </div>"""


def calendar_html(rows: list[dict]) -> str:
    weeks = []
    for w in sorted({r["week"] for r in rows}):
        items = "".join(
            f'<li><span class="day">{md_inline(r["day"])}</span><span class="what">{md_inline(r["what"])}</span>'
            f'{"<span class=stories>Сторис: " + md_inline(r["stories"]) + "</span>" if r["stories"] not in ("—", "") else ""}</li>'
            for r in rows if r["week"] == w)
        weeks.append(f'<section class="week"><h3>Неделя {w}</h3><ul>{items}</ul></section>')
    return "".join(weeks)


HOOK_SECONDS = 4.5  # variants differ only in their opening


def ffmpeg(src: Path, dst: Path, *args: str) -> None:
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), *args, str(dst)], check=True)


def media(data: dict) -> None:
    out = OUT / "media"
    out.mkdir(parents=True, exist_ok=True)
    for reel in REELS:
        draft = ADS / "out" / reel / f"{reel}-draft"
        ffmpeg(draft.with_suffix(".mp4"), out / f"{reel}.mp4", "-vf", "scale=720:1280:flags=lanczos", "-c:v", "libx264",
               "-preset", "slow", "-crf", "27", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart")
        ffmpeg(Path(f"{draft}-cover.jpg"), out / f"{reel}.jpg", "-vf", "scale=720:-2", "-q:v", "4")
    for reel in HOOK_REELS:
        for h in data[reel]["hooks"]:
            name = f"{reel}-draft" if h["id"] == "a" else f"{reel}-hook-{h['id']}"
            ffmpeg(ADS / "out" / reel / f"{name}.mp4", out / f"{reel}-hook-{h['id']}.mp4", "-t", str(HOOK_SECONDS), "-an",
                   "-vf", "scale=360:640:flags=lanczos", "-c:v", "libx264", "-preset", "slow", "-crf", "28",
                   "-pix_fmt", "yuv420p", "-movflags", "+faststart")


def main() -> None:
    scripts = (CAMPAIGN / "scripts.md").read_text(encoding="utf-8")
    captions = (CAMPAIGN / "captions.md").read_text(encoding="utf-8")
    calendar = (CAMPAIGN / "calendar.md").read_text(encoding="utf-8")
    data = {r: reel_data(r, scripts, captions) for r in REELS}
    media(data)

    layers = "".join(f"""
    <section class="layer" id="layer-{key}">
      <header class="layer-head"><h3>{html.escape(name)}</h3><p>{html.escape(note)}</p></header>
      <div class="reels">{''.join(reel_card(data[r]) for r in reels)}</div>
    </section>""" for key, name, note, reels in LAYERS)
    hooks = "".join(hook_block(data[r]) for r in HOOK_REELS)
    page = TEMPLATE.replace("{{LAYERS}}", layers).replace("{{HOOKS}}", hooks) \
        .replace("{{CALENDAR}}", calendar_html(calendar_rows(calendar))) \
        .replace("{{TELEPROMPTER}}", TELEPROMPTER).replace("{{PR_URL}}", PR_URL)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(OUT / "index.html")


TEMPLATE = (CAMPAIGN / "page_template.html").read_text(encoding="utf-8")

if __name__ == "__main__":
    main()
