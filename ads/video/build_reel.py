"""Build a reel's HyperFrames composition from its beat sheet and voice-over timings.

    python ads/video/build_reel.py r03          -> ads/video/index.html (the reel built last)
    npx hyperframes render -o ../out/r03/r03.mp4   (from ads/video)

Inputs:
  ads/campaign/reels/<reel>.json        which clip plays under which words, labels, end card
  ads/cache/vo/<reel>.words.json        word timings (ads/audio/prep_vo.py)
  ads/video/assets/clips/<reel>/manifest.json   clip lengths (ads/mining/prep_clips.py)

Everything is anchored to words, so re-recording the voice-over and re-running this
script re-times cuts, labels and captions without touching the beat sheet.
Anchors: "start", "line:N", "line:N:word" (first word in line N starting with "word"),
or a bare "word" inside the current beat's line.

A shot is a lesson clip ("clip"; "r03/s01-tear" borrows another reel's clip), a photo of a finished
work ("photo": "<slug>/<file stem>" from frontend/public/works), a grid of every counted photo (or of
the reel's "grid" list) ("grid": true) or a graphic card ("card": "modules" | "tariffs" | "calc").
Photos with "count" and "name" get the 01..11 counter instead of captions. Any shot may carry
"stats" (big numbers over the window), "tone": "mono" (desaturated) and, for a clip,
"frame": "phone" (played on a phone screen). A reel may carry a "scheme": a diagram card in the
window's corner that draws itself step by step under the voice.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import shutil
from functools import lru_cache
from pathlib import Path

VIDEO = Path(__file__).resolve().parent
ADS = VIDEO.parent
SFX_KIT = ADS / "vendor" / "opus-sound-layer" / "audio" / "kit"
WORKS = ADS.parent / "frontend" / "public" / "works"

VO_DELAY = 0.2          # voice starts slightly after frame 0 so captions never look pre-existing
FRAME = 1 / 30
MIN_RATE = 0.5          # clips are 60 fps: down to half speed still gives 30 real frames per second
MIN_SHOT = 0.9          # s; shorter shots read as flicker
CAPTION_WORDS = 5
CAPTION_CHARS = 26      # one line at 54 px inside the window
CAPTION_BREAK = re.compile(r"[.,?!:;—–]$")
CAPTION_HOLD = 0.8      # s a group may stay after its last word when nothing replaces it
CAPTION_MIN = 0.6       # s; a group the end card would cut sooner is not shown at all
DANGLING = {"в", "во", "с", "со", "и", "к", "о", "у", "а", "на", "по", "за", "из", "от", "до", "не"}

# Sounds picked from the CC0 kit by type and metadata (they were not auditioned).
SFX = {
    "pop": ["pop/fs-503162-mouth-pops-magic-bottle-cork-3", "pop/fs-206152-bottlepop44-wav-1"],
    "swish": ["swish/fs-14175-27-wav-1", "swish/fs-388003-double-swish-1"],
    "shimmer": ["shimmer/fs-462095-sparkling-star-01-wav-2"],
    "thump": ["thump/fs-389999-thump-cloth-1"],
    "end": ["shimmer/fs-376745-fantasy-ui-button-3-wav-2"],
    "tick": ["tick/fs-398275-clock-tick-1", "tick/fs-398275-clock-tick-2", "tick/fs-398275-clock-tick-3"],
}
SFX_GAIN = {"pop": 0.35, "swish": 0.3, "shimmer": 0.35, "thump": 0.45, "end": 0.3, "tick": 0.4}
STAT_W, STAT_GAP = 440, 40  # px; big-number plates over the window
HEAD_SIZES, HEAD_WIDTH = (68, 76), 920  # px; headline lines (as in #h0/#h1) and the widest a line may get


def clip_path(reel: str, clip: str) -> str:
    """'s01-tear' is this reel's clip; 'r03/s01-tear' borrows a clip cut for another reel."""
    return clip if "/" in clip else f"{reel}/{clip}"


@lru_cache
def manifest(owner: str) -> dict:
    return json.loads((VIDEO / "assets" / "clips" / owner / "manifest.json").read_text(encoding="utf-8"))


def clip_info(reel: str, clip: str) -> dict:
    owner, name = clip_path(reel, clip).split("/")
    return manifest(owner)[f"{name}.mp4"]


def norm(word: str) -> str:
    return re.sub(r"[^\w-]", "", word.lower().replace("ё", "е"))


class Timing:
    def __init__(self, words: dict):
        self.lines = words["lines"]
        self.vo_end = VO_DELAY + words["duration"]

    def line_start(self, n: int) -> float:
        return VO_DELAY + self.lines[n]["start"]

    def word_start(self, n: int, prefix: str) -> float:
        want = norm(prefix)
        for w in self.lines[n]["words"]:
            if norm(w["text"]).startswith(want):
                return VO_DELAY + w["start"]
        raise SystemExit(f"anchor '{prefix}' not found in line {n}: {self.lines[n]['text']}")

    def anchor(self, ref: str | None, line: int | None = None) -> float:
        if ref in (None, "start"):
            return 0.0 if ref == "start" or line is None else self.line_start(line)
        if ref.startswith("line:"):
            parts = ref.split(":")
            n = int(parts[1])
            return self.word_start(n, parts[2]) if len(parts) > 2 else self.line_start(n)
        return self.word_start(line, ref)


def chars(ws: list[dict]) -> int:
    return len(" ".join(w["text"] for w in ws))


def split_phrase(ws: list[dict]) -> list[list[dict]]:
    """Split one phrase into the fewest caption groups that fit, of even length.

    A group never ends on "в", "с", "и" (the short word goes on with the words it belongs to),
    and a last group of one word ("раза.") is avoided when a better cut exists."""
    n = min(len(ws), max(math.ceil(len(ws) / CAPTION_WORDS), math.ceil(chars(ws) / CAPTION_CHARS)))
    out, rest = [], ws
    for k in range(n, 1, -1):
        target = chars(rest) / k
        scored = []
        for cut in range(1, len(rest) - k + 2):
            if norm(rest[cut - 1]["text"]) in DANGLING:
                continue
            orphan = 6 if k == 2 and len(rest) - cut == 1 else 0
            scored.append((abs(chars(rest[:cut]) - target) + orphan, cut))
        cut = min(scored)[1] if scored else max(1, len(rest) - k + 1)
        out.append(rest[:cut])
        rest = rest[cut:]
    out.append(rest)
    return out


def caption_groups(timing: Timing, until: float, skip: set[int], counter: tuple[float, float] | None) -> list[dict]:
    groups = []
    for n, line in enumerate(timing.lines):
        if n in skip:
            continue
        # Dashes are dropped from the timed words; a dash in the script still ends a phrase.
        dashes, k = set(), -1
        for token in line["text"].split():
            if norm(token):
                k += 1
            elif k >= 0:
                dashes.add(k)
        if k + 1 != len(line["words"]):
            dashes = set()
        phrase: list[dict] = []
        for wi, w in enumerate(line["words"]):
            if w["text"] in {"—", "–"}:
                continue
            phrase.append(w)
            if CAPTION_BREAK.search(w["text"]) or wi in dashes:
                groups += split_phrase(phrase)
                phrase = []
        if phrase:
            groups += split_phrase(phrase)
    out = []
    for i, g in enumerate(groups):
        start = VO_DELAY + g[0]["start"] - 0.05
        if start >= until - CAPTION_MIN:  # cut off by the end card before it can be read
            break
        nxt = VO_DELAY + groups[i + 1][0]["start"] - 0.05 if i + 1 < len(groups) else VO_DELAY + g[-1]["end"] + 0.3
        # The next group replaces this one (two on screen overlap); across a skipped line it just fades out.
        end = min(nxt, VO_DELAY + g[-1]["end"] + CAPTION_HOLD, until)
        if counter and start < counter[1] and end > counter[0]:  # the counter plate sits where captions do
            if start < counter[0]:
                end = counter[0]
            elif end - counter[1] >= 0.4:
                start = counter[1]
            else:
                continue
        out.append({"start": max(start, 0.1), "end": end,
                    "words": [{"text": w["text"], "start": VO_DELAY + w["start"], "end": VO_DELAY + w["end"]} for w in g]})
    return out


def plan(spec: dict, timing: Timing, reel: str) -> dict:
    end = spec["end"]
    end_start = timing.anchor(end["from"])
    total = max(timing.vo_end, end_start) + end.get("tail", 1.2)
    min_shot = spec.get("min_shot", MIN_SHOT)  # a counted list reads fine at quicker cuts

    slots = []
    for bi, beat in enumerate(spec["beats"]):
        for ci, c in enumerate(beat["clips"]):
            start = 0.0 if bi == 0 and ci == 0 else timing.anchor(c.get("from"), beat["line"])
            slots.append({**c, "start": start, "line": beat["line"]})
    # A quick list ("базу, праймер или клей") would give sub-second shots nobody can read:
    # hold each shot at least MIN_SHOT and let the following cuts slip slightly behind their words.
    for i in range(1, len(slots)):
        slots[i]["start"] = max(slots[i]["start"], slots[i - 1]["start"] + min_shot)
    end_start = max(end_start, slots[-1]["start"] + min_shot)
    total = max(total, end_start + end.get("tail", 1.2))
    for i, s in enumerate(slots):
        s["end"] = slots[i + 1]["start"] if i + 1 < len(slots) else end_start
    shot = {k: end[k] for k in ("clip", "photo") if k in end}
    slots.append({**shot, "start": end_start, "end": total, "line": None, "is_end": True})

    def at(s: dict, ref: str | None) -> float:
        return max(s["start"], timing.anchor(ref, s["line"])) if ref else s["start"]

    for s in slots:
        s["dur"] = s["end"] - s["start"]
        if "clip" in s:
            clip = clip_info(reel, s["clip"])
            s["rate"] = round(min(1.0, clip["duration"] / s["dur"]), 3)
            if s["rate"] < MIN_RATE:
                raise SystemExit(f"{s['clip']} lasts {clip['duration']}s but its slot is {s['dur']:.2f}s; "
                                 f"cut a longer clip (needs >= {s['dur'] * MIN_RATE:.2f}s)")
        if "label" in s:
            s["label_start"] = at(s, s.get("label_at"))
        for key in ("stats", "steps"):
            if key in s:
                s[key] = [{**item, "start": at(s, item.get("at"))} for item in s[key]]
        if "focus_at" in s:
            s["focus_start"] = at(s, s["focus_at"])

    heads = []
    for h in spec["headline"]:
        heads.append({**h, "start": timing.anchor(h["at"])})
    scheme = None
    if "scheme" in spec:  # anchors here are absolute ("line:N:word"): the scheme spans several beats
        sc = spec["scheme"]
        scheme = {**sc, "start": timing.anchor(sc["from"]), "end": min(timing.anchor(sc["to"]), end_start),
                  "marks": [{**m, "start": timing.anchor(m["at"])} for m in sc["marks"]]}
    counted = [s for s in slots if "count" in s]
    counter = (counted[0]["start"], counted[-1]["end"]) if counted else None
    return {"slots": slots, "end_start": end_start, "total": round(total, 3), "heads": heads,
            "grid": [s["photo"] for s in counted] or spec.get("grid", []), "scheme": scheme,
            "captions": caption_groups(timing, end_start, set(spec.get("captions_skip_lines", [])), counter)}


def sfx_cues(p: dict) -> list[dict]:
    cues, used = [], {}
    def add(kind: str, at: float):
        takes = SFX[kind]
        take = takes[used.get(kind, 0) % len(takes)]
        used[kind] = used.get(kind, 0) + 1
        cues.append({"kind": kind, "id": take, "at": at})
    for s in p["slots"]:
        if s.get("sfx"):
            add(s["sfx"], s["start"])
        if "label" in s:
            add("pop", s["label_start"])
        if "count" in s:
            add("tick", s["start"])
        for item in s.get("stats", []) + s.get("steps", []):
            if item.get("sfx", "pop"):  # "sfx": null keeps a step that lands with another one quiet
                add(item.get("sfx", "pop"), item["start"])
        if "focus_start" in s:
            add("shimmer", s["focus_start"])
    for h in p["heads"]:
        if h.get("sfx"):
            add(h["sfx"], h["start"])
    add("end", p["end_start"] + 0.25)
    return cues


def photo_src(photo: str) -> str:
    return f"assets/photos/{Path(photo).name}.webp"


def copy_assets(reel: str, p: dict, cues: list[dict], vo_src: Path) -> dict:
    photo_dir = VIDEO / "assets" / "photos"
    photo_dir.mkdir(parents=True, exist_ok=True)
    for photo in {s["photo"] for s in p["slots"] if "photo" in s} | set(p["grid"]):
        dst = VIDEO / photo_src(photo)
        if not dst.exists():
            shutil.copy(WORKS / f"{photo}.webp", dst)
    sfx_dir = VIDEO / "assets" / "sfx"
    sfx_dir.mkdir(parents=True, exist_ok=True)
    meta = json.loads((SFX_KIT / "catalog.json").read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in meta["sounds"]}
    info = {}
    for c in cues:
        snd = by_id[c["id"]]
        dst = sfx_dir / Path(snd["file"]).name
        if not dst.exists():
            shutil.copy(SFX_KIT / snd["file"], dst)
        info[c["id"]] = {"src": f"assets/sfx/{dst.name}", "peak": snd["peak_offset_s"], "dur": snd["dur_s"]}
    vo_dir = VIDEO / "assets" / "vo"
    vo_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(vo_src, vo_dir / f"{reel}.wav")
    return info


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def scheme_html(sc: dict) -> tuple[str, list[str]]:
    """A small diagram card in the window's corner that draws itself step by step under the voice,
    while the footage below shows the same step done by hand. Shapes are in the card's 300x400 box:
    "dot" pops in, "line" draws itself, "guide" (dashed) and "fill" fade in."""
    shapes, tl = [sc.get("base", "")], []
    for k, m in enumerate(sc["marks"]):
        mid = f"sc{k}"
        if m["type"] == "dot":
            shapes.append(f'<circle id="{mid}" class="dot" cx="{m["x"]}" cy="{m["y"]}" r="9" />')
            tl.append(f'tl.fromTo("#{mid}", {{scale: 0, opacity: 0, transformOrigin: "50% 50%"}}, '
                      f'{{scale: 1, opacity: 1, duration: 0.25, ease: "back.out(2.4)"}}, {m["start"]:.3f});')
        elif m["type"] == "line":
            shapes.append(f'<path id="{mid}" class="line" d="{m["d"]}" pathLength="1" />')
            tl.append(f'tl.fromTo("#{mid}", {{strokeDashoffset: 1, opacity: 1}}, '
                      f'{{strokeDashoffset: 0, duration: {m.get("draw", 0.45)}, ease: "power2.inOut"}}, {m["start"]:.3f});')
        else:
            shapes.insert(1, f'<path id="{mid}" class="{m["type"]}" d="{m["d"]}" />')  # under the dots and lines
            tl.append(f'tl.fromTo("#{mid}", {{opacity: 0}}, {{opacity: 1, duration: 0.35, ease: "power1.out"}}, {m["start"]:.3f});')
    tl.insert(0, f'tl.fromTo("#scheme", {{scale: 0.8, opacity: 0}}, {{scale: 1, opacity: 1, duration: 0.3, '
                 f'ease: "back.out(1.8)"}}, {sc["start"]:.3f});')
    html_ = (f'<div class="scheme clip" id="scheme" data-start="{sc["start"]:.3f}" '
             f'data-duration="{sc["end"] - sc["start"]:.3f}" data-track-index="3">'
             f'<svg viewBox="0 0 300 400" xmlns="http://www.w3.org/2000/svg">{"".join(shapes)}</svg></div>')
    return html_, tl


def card_html(i: int, s: dict, p: dict, timed: str) -> tuple[str, list[str]]:
    """A graphic card in place of footage: the course's lessons, its two tariffs, or a price worked out step by step."""
    kind, start, tl = s["card"], s["start"], []
    if kind == "modules":
        body = "".join(f'<div class="row"><b>{k:02d}</b><span>{esc(title)}</span><i>{esc(length)}</i></div>'
                       for k, (title, length) in enumerate(s["rows"], start=1))
        tl.append(f'tl.fromTo("#v{i} .row", {{x: -30, opacity: 0}}, {{x: 0, opacity: 1, duration: 0.25, '
                  f'ease: "power3.out", stagger: 0.07}}, {start:.3f});')
    elif kind == "tariffs":
        body = ""
        for k, t in enumerate(s["tariffs"]):
            feats = "".join(f"<li>{esc(f)}</li>" for f in t["features"])
            body += f'<div class="tariff t{k}"><h3>{esc(t["title"])}</h3><b>{esc(t["price"])}</b><ul>{feats}</ul></div>'
        tl.append(f'tl.fromTo("#v{i} .tariff", {{y: 40, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.35, '
                  f'ease: "power3.out", stagger: 0.15}}, {start:.3f});')
        if "focus_start" in s:  # the voice turns to the second tariff: it steps forward, the first steps back
            tl.append(f'tl.to("#v{i} .t0", {{opacity: 0.45, scale: 0.95, duration: 0.3, ease: "power2.out"}}, {s["focus_start"]:.3f});')
            tl.append(f'tl.to("#v{i} .t1", {{scale: 1.05, duration: 0.3, ease: "back.out(2)"}}, {s["focus_start"]:.3f});')
    elif kind == "calc":
        photos = (p["grid"] * 2)[:12]  # fill all 12 cells: an empty one reads as a missing photo
        ghost = "".join(f'<img src="{photo_src(ph)}" alt="" />' for ph in photos)
        body = f'<div class="ghost">{ghost}</div>'
        for k, step in enumerate(s["steps"]):
            sid = f"v{i}s{k}"
            body += f'<div class="step {step.get("style", "mid")}" id="{sid}">{esc(step["text"].format(step.get("count", "")))}</div>'
            if step["start"] > 0:  # a step already there on frame 0 is part of the cover
                tl.append(f'tl.fromTo("#{sid}", {{y: 30, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.3, '
                          f'ease: "power3.out"}}, {step["start"]:.3f});')
            if "count" in step:  # the number runs up to its value as it lands
                fmt = json.dumps(step["text"])
                tl.append(f'tl.fromTo({{n: 0}}, {{n: 0}}, {{n: {step["count"]}, duration: 0.7, ease: "power2.out", '
                          f'onUpdate() {{ document.getElementById("{sid}").textContent = '
                          f'{fmt}.replace("{{}}", Math.round(this.targets()[0].n)); }}}}, {step["start"]:.3f});')
    else:
        raise SystemExit(f"unknown card '{kind}'")
    single = " single" if kind == "tariffs" and len(s["tariffs"]) == 1 else ""  # one price card fills the window
    return f'<div id="v{i}" class="card {kind}{single} clip" {timed}>{body}</div>', tl


def render_html(reel: str, spec: dict, p: dict, cues: list[dict], sfx_info: dict, vo_dur: float) -> str:
    T = p["total"]
    end = spec["end"]
    footage, parts, tl = [], [], []  # footage goes inside the window, parts are overlays on the page

    # Footage: an untimed wrapper per shot carries the camera move; the element inside is the timed clip.
    for i, s in enumerate(p["slots"]):
        timed = f'data-start="{s["start"]:.3f}" data-duration="{s["dur"]:.3f}" data-track-index="1"'
        tone = " mono" if s.get("tone") == "mono" else ""
        if "clip" in s:
            phone = s.get("frame") == "phone"
            inner = (f'<video id="v{i}" class="clip{tone}{" on-phone" if phone else ""}" '
                     f'src="assets/clips/{clip_path(reel, s["clip"])}.mp4" {timed} '
                     f'data-playback-rate="{s["rate"]}" muted playsinline></video>')
            move = f'{{scale: 1.0}}, {{scale: {1.08 if s.get("is_end") else 1.05}, duration: {s["dur"]:.3f}, ease: "none"}}'
            if phone:
                # The phone is a timed sibling under the video (an untimed one would cover earlier shots, and a
                # video nested in a timed element gets its frames out of step); the video sits on its screen.
                inner = f'<div class="backdrop clip" {timed}><div class="phone"></div></div>' + inner
                move = f'{{scale: 1.0}}, {{scale: 1.04, duration: {s["dur"]:.3f}, ease: "power2.out"}}'
        elif "photo" in s:
            # A still needs more motion than footage: it lands zoomed in and settles.
            inner = f'<img id="v{i}" class="clip{tone}" src="{photo_src(s["photo"])}" alt="" {timed} />'
            move = f'{{scale: 1.14}}, {{scale: 1.03, duration: {s["dur"]:.3f}, ease: "power2.out"}}'
        elif "card" in s:
            inner, card_tl = card_html(i, s, p, timed)
            tl += card_tl
            move = f'{{scale: 1.0}}, {{scale: 1.02, duration: {s["dur"]:.3f}, ease: "none"}}'
        else:
            cells = "".join(f'<div class="cell"><img src="{photo_src(ph)}" alt="" /></div>' for ph in p["grid"])
            cells += f'<div class="cell total"><b>{len(p["grid"])}</b><span>техник</span></div>'
            inner = f'<div id="v{i}" class="grid clip" {timed}>{cells}</div>'
            move = f'{{scale: 1.0}}, {{scale: 1.04, duration: {s["dur"]:.3f}, ease: "none"}}'
            if s.get("intro"):
                tl.append(f'tl.fromTo("#v{i} .cell", {{scale: 0.6, opacity: 0}}, {{scale: 1, opacity: 1, duration: 0.3, '
                          f'ease: "back.out(1.7)", stagger: 0.05}}, {s["start"]:.3f});')
            else:
                # Already in place on frame 0 (it is the cover); a light ripple across the cells gives motion.
                tl.append(f'tl.to("#v{i} .cell", {{scale: 1.05, duration: 0.16, yoyo: true, repeat: 1, '
                          f'ease: "sine.inOut", stagger: 0.09}}, {s["start"] + 0.15:.3f});')
        footage.append(f'<div class="shot" id="w{i}">{inner}</div>')
        tl.append(f'tl.fromTo("#w{i}", {move}, {s["start"]:.3f});')

    # Counter for a counted list: one dark plate, the number and name change on every cut.
    counted = [s for s in p["slots"] if "count" in s]
    if counted:
        first, last = counted[0]["start"], counted[-1]["end"]
        parts.append(f'<div class="count-plate clip" id="plate" data-start="{first:.3f}" '
                     f'data-duration="{last - first:.3f}" data-track-index="3"></div>')
        tl.append(f'tl.fromTo("#plate", {{scaleX: 0.7, opacity: 0}}, {{scaleX: 1, opacity: 1, duration: 0.2, '
                  f'ease: "power3.out"}}, {first:.3f});')
        for k, s in enumerate(counted):
            parts.append(f'<div class="count clip" id="n{k}" data-start="{s["start"]:.3f}" '
                         f'data-duration="{s["dur"]:.3f}" data-track-index="4">'
                         f'<b>{s["count"]:02d}</b><span>{esc(s["name"])}</span></div>')
            tl.append(f'tl.fromTo("#n{k} b", {{y: 36, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.18, '
                      f'ease: "power3.out"}}, {s["start"]:.3f});')
            tl.append(f'tl.fromTo("#n{k} span", {{x: -18, opacity: 0}}, {{x: 0, opacity: 1, duration: 0.18, '
                      f'ease: "power3.out"}}, {s["start"] + 0.04:.3f});')

    # Big numbers over the window ("~5 ч практики", "30 дней доступа"): side by side, each from its word on.
    for i, s in enumerate(p["slots"]):
        stats = s.get("stats", [])
        for k, st in enumerate(stats):
            left = 540 - STAT_W * len(stats) / 2 - STAT_GAP * (len(stats) - 1) / 2 + k * (STAT_W + STAT_GAP)
            parts.append(f'<div class="stat clip" id="st{i}x{k}" style="left: {left:.0f}px" data-start="{st["start"]:.3f}" '
                         f'data-duration="{s["end"] - st["start"]:.3f}" data-track-index="3">'
                         f'<b>{esc(st["big"])}</b><span>{esc(st["small"])}</span></div>')
            tl.append(f'tl.fromTo("#st{i}x{k}", {{scale: 0.7, opacity: 0}}, {{scale: 1, opacity: 1, duration: 0.3, '
                      f'ease: "back.out(1.8)"}}, {st["start"]:.3f});')

    if p["scheme"]:
        scheme, scheme_tl = scheme_html(p["scheme"])
        parts.append(scheme)
        tl += scheme_tl

    # Speaker tag at the very start, then technique labels, all in the same corner of the window.
    tags = [{"text": spec["speaker"], "start": 0.35, "end": min(2.6, p["slots"][1]["start"]), "kind": "speaker"}] \
        if spec.get("speaker") else []
    tags += [{"text": s["label"], "start": s["label_start"], "end": s["end"], "kind": "label"}
             for s in p["slots"] if "label" in s]
    for i, t in enumerate(tags):
        parts.append(f'<div class="tag clip {t["kind"]}" id="tag{i}" data-start="{t["start"]:.3f}" '
                     f'data-duration="{t["end"] - t["start"]:.3f}" data-track-index="3"><span>{esc(t["text"])}</span></div>')
        tl.append(f'tl.fromTo("#tag{i} span", {{y: 18, scale: 0.9, opacity: 0}}, '
                  f'{{y: 0, scale: 1, opacity: 1, duration: 0.24, ease: "back.out(2)"}}, {t["start"]:.3f});')

    # Headline above the window: the hook stays as the reel's title until the end card.
    for i, h in enumerate(p["heads"]):
        cls = "head-line accent" if h.get("accent") else "head-line"
        # A long line shrinks to stay clear of the frame edges (Playfair averages ~0.53 em a character).
        base = HEAD_SIZES[min(i, len(HEAD_SIZES) - 1)]
        size = min(base, int(HEAD_WIDTH / (len(h["text"]) * 0.53)))
        fit = f' style="font-size: {size}px"' if size < base else ""
        parts.append(f'<div class="{cls} clip" id="h{i}"{fit} data-start="{h["start"]:.3f}" '
                     f'data-duration="{p["end_start"] - h["start"]:.3f}" data-track-index="2">'
                     f'<span>{esc(h["text"])}</span></div>')
        if h["start"] > 0:
            tl.append(f'tl.fromTo("#h{i} span", {{y: 34, opacity: 0}}, '
                      f'{{y: 0, opacity: 1, duration: 0.32, ease: "power3.out"}}, {h["start"]:.3f});')

    # Captions: one group at a time, the spoken word lit.
    caps = []
    for gi, g in enumerate(p["captions"]):
        spans = "".join(f'<span class="w" id="c{gi}w{wi}">{esc(w["text"])}</span> ' for wi, w in enumerate(g["words"]))
        caps.append(f'<div class="cap clip" id="c{gi}" data-start="{g["start"]:.3f}" '
                    f'data-duration="{g["end"] - g["start"]:.3f}" data-track-index="4"><p>{spans.strip()}</p></div>')
        tl.append(f'tl.fromTo("#c{gi} p", {{y: 10, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.1}}, {g["start"]:.3f});')
        for wi, w in enumerate(g["words"]):
            tl.append(f'tl.set("#c{gi}w{wi}", {{color: "#ffc9d8"}}, {w["start"]:.3f});')
            if wi < len(g["words"]) - 1:
                tl.append(f'tl.set("#c{gi}w{wi}", {{color: "#ffffff"}}, {g["words"][wi + 1]["start"]:.3f});')
    parts.append('<div id="captions" class="captions-host">' + "".join(caps) + "</div>")

    # End card.
    es, ed = p["end_start"], T - p["end_start"]
    parts.append(
        f'<div class="end clip" id="end" data-start="{es:.3f}" data-duration="{ed:.3f}" data-track-index="2">'
        f'<div class="end-title"><span>{esc(end["title"])}</span></div>'
        f'<div class="end-sub"><span>{esc(end["sub"])}</span></div></div>'
        f'<div class="cta clip" id="cta" data-start="{es + 0.2:.3f}" data-duration="{ed - 0.2:.3f}" data-track-index="4">'
        f'<span>{esc(end["cta"])}<i>→</i></span></div>')
    tl.append(f'tl.fromTo("#end .end-title span", {{y: 40, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.4, ease: "power3.out"}}, {es:.3f});')
    tl.append(f'tl.fromTo("#end .end-sub span", {{y: 24, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.4, ease: "power3.out"}}, {es + 0.12:.3f});')
    tl.append(f'tl.fromTo("#cta span", {{scale: 0.6, opacity: 0}}, {{scale: 1, opacity: 1, duration: 0.35, ease: "back.out(2.2)"}}, {es + 0.25:.3f});')
    for k, at in enumerate((es + 1.1, es + 2.0)):
        if at + 0.4 < T:
            tl.append(f'tl.to("#cta span", {{scale: 1.06, duration: 0.2, yoyo: true, repeat: 1, ease: "sine.inOut"}}, {at:.3f});')

    # Sound: voice-over and effects, each effect's peak one frame after its picture.
    audio = [f'<audio id="vo" src="assets/vo/{reel}.wav" data-start="{VO_DELAY}" data-duration="{vo_dur:.3f}" '
             f'data-volume="1" data-track-index="5"></audio>']
    for k, c in enumerate(cues):
        info = sfx_info[c["id"]]
        at = max(0.0, c["at"] + FRAME - info["peak"])
        dur = min(info["dur"], T - at)
        audio.append(f'<audio id="sfx{k}" src="{info["src"]}" data-start="{at:.3f}" data-duration="{dur:.3f}" '
                     f'data-volume="{SFX_GAIN[c["kind"]]}" data-track-index="{6 + k % 2}"></audio>')

    return TEMPLATE.format(
        reel=reel, total=f"{T:.3f}", footage="\n        ".join(footage), body="\n      ".join(parts),
        audio="\n      ".join(audio), timeline="\n      ".join(tl))


TEMPLATE = """<!doctype html>
<html lang="ru" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <!-- Generated by ads/video/build_reel.py from ads/campaign/reels/{reel}.json; edit those, not this file. -->
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "LS Display"; src: url("assets/fonts/PlayfairDisplay.ttf"); font-weight: 400 900; font-style: normal; }}
      @font-face {{ font-family: "LS Display"; src: url("assets/fonts/PlayfairDisplay-Italic.ttf"); font-weight: 400 900; font-style: italic; }}
      @font-face {{ font-family: "LS Sans"; src: url("assets/fonts/Inter.ttf"); font-weight: 100 900; }}
      :root {{
        --blush: #fff1f4;
        --blush-deep: #f6dbe2;
        --ink: #3a2a2e;
        --rose: #c8325f;
        --rose-hi: #db3f6e;
        --gold: #b8913a;
        --lit: #ffc9d8;
        --display: "LS Display", Georgia, serif;
        --sans: "LS Sans", Arial, sans-serif;
      }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: var(--blush); }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden;
        background: linear-gradient(180deg, #fff1f4 0%, #fbe6eb 55%, var(--blush-deep) 100%); font-family: var(--sans); }}
      .brand {{ position: absolute; left: 0; right: 0; top: 100px; text-align: center; font: 700 28px var(--sans);
        letter-spacing: 0.42em; color: #8f6c26; }}
      .head-line {{ position: absolute; left: 0; right: 0; text-align: center; font-family: var(--display);
        font-weight: 600; color: var(--ink); line-height: 1.05; }}
      #h0 {{ top: 196px; font-size: 68px; }}
      #h1 {{ top: 290px; font-size: 76px; }}
      .head-line.accent {{ color: var(--rose); font-style: italic; }}
      .head-line span {{ display: inline-block; }}
      .window {{ position: absolute; left: 32px; top: 452px; width: 1016px; height: 878px; border-radius: 44px;
        overflow: hidden; background: #2a2024; box-shadow: 0 26px 60px rgba(120, 40, 70, 0.22); }}
      .shot {{ position: absolute; inset: 0; transform-origin: 50% 45%; }}
      .shot video, .shot > img {{ position: absolute; left: 0; top: 0; width: 1016px; height: 878px; object-fit: cover; object-position: 50% 40%; }}
      .grid {{ position: absolute; left: 0; top: 0; width: 1016px; height: 878px; padding: 14px 14px 178px;
        display: grid; grid-template-columns: repeat(4, 1fr); grid-template-rows: repeat(3, 1fr); gap: 10px;
        background: linear-gradient(180deg, #fbe6eb 0%, var(--blush-deep) 100%); }}
      .cell {{ position: relative; border-radius: 18px; overflow: hidden; box-shadow: 0 6px 16px rgba(120, 40, 70, 0.18); }}
      .cell img {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
      .cell.total {{ display: flex; flex-direction: column; align-items: center; justify-content: center;
        background: linear-gradient(135deg, var(--rose-hi), #b02a52); color: #ffffff; }}
      .cell.total b {{ font: italic 700 112px/0.9 var(--display); }}
      .cell.total span {{ margin-top: 10px; font: 800 30px var(--sans); letter-spacing: 0.14em; text-transform: uppercase; color: #ffe3ea; }}
      .count-plate {{ position: absolute; left: 170px; top: 1158px; width: 740px; height: 132px; border-radius: 999px;
        background: rgba(42, 22, 30, 0.8); box-shadow: 0 12px 30px rgba(42, 22, 30, 0.3); }}
      .count {{ position: absolute; left: 170px; top: 1158px; width: 740px; height: 132px; display: flex;
        align-items: center; justify-content: center; gap: 28px; }}
      .count b {{ font: italic 700 96px/1 var(--display); color: var(--lit); }}
      .count span {{ font: 800 56px var(--sans); color: #ffffff; letter-spacing: 0.06em; text-transform: uppercase; }}
      .mono {{ filter: grayscale(1) contrast(0.92) brightness(1.06); }}
      .scheme {{ position: absolute; left: 724px; top: 476px; width: 300px; height: 400px; border-radius: 28px;
        background: rgba(255, 255, 255, 0.95); box-shadow: 0 14px 34px rgba(60, 20, 35, 0.28); }}
      .scheme svg {{ width: 300px; height: 400px; }}
      .scheme .nail {{ fill: #f7cfd9; stroke: #e7a9b9; stroke-width: 3; }}
      .scheme .dot {{ fill: var(--rose); stroke: #ffffff; stroke-width: 3; opacity: 0; }}
      .scheme .line {{ fill: none; stroke: var(--rose); stroke-width: 5; stroke-linecap: round; stroke-dasharray: 1;
        stroke-dashoffset: 1; opacity: 0; }}
      .scheme .guide {{ fill: none; stroke: #b07a88; stroke-width: 2.5; stroke-dasharray: 7 7; opacity: 0; }}
      .scheme .fill {{ fill: #ffffff; stroke: var(--rose); stroke-width: 3; opacity: 0; }}
      .backdrop, .card {{ position: absolute; left: 0; top: 0; width: 1016px; height: 878px;
        background: linear-gradient(180deg, #fff6f8 0%, #fbe6eb 60%, var(--blush-deep) 100%); }}
      .phone {{ position: absolute; left: 88px; top: 110px; width: 840px; height: 452px;
        border-radius: 64px; background: #1d1519; box-shadow: 0 30px 60px rgba(90, 30, 50, 0.35); }}
      .shot video.on-phone {{ left: 122px; top: 136px; width: 772px; height: 400px; border-radius: 30px; }}
      .card.modules {{ padding: 30px 64px 186px; display: flex; flex-direction: column; justify-content: space-between; }}
      .modules .row {{ display: flex; align-items: baseline; gap: 22px; padding-bottom: 6px;
        border-bottom: 2px solid rgba(200, 50, 95, 0.12); font: 600 36px/1 var(--sans); color: var(--ink); }}
      .modules .row b {{ width: 56px; font: italic 700 36px/1 var(--display); color: var(--rose); }}
      .modules .row span {{ flex: 1; }}
      .modules .row i {{ font-style: normal; font-weight: 500; font-size: 32px; color: #8a6a72; }}
      .card.tariffs {{ display: flex; align-items: center; gap: 28px; padding: 30px 40px 190px; }}
      .tariff {{ flex: 1; max-width: 560px; margin: 0 auto; padding: 40px 34px; border-radius: 36px; background: #ffffff;
        box-shadow: 0 14px 34px rgba(120, 40, 70, 0.16); }}
      .tariff h3 {{ font: 800 30px var(--sans); letter-spacing: 0.06em; text-transform: uppercase; color: var(--ink); }}
      .tariff b {{ display: block; margin: 20px 0 26px; font: italic 700 80px/1 var(--display); color: var(--rose); }}
      .tariff ul {{ list-style: none; }}
      .tariff li {{ position: relative; margin-top: 12px; padding-left: 42px; font: 600 32px/1.25 var(--sans); color: var(--ink); }}
      .tariff li::before {{ content: "✓"; position: absolute; left: 0; color: var(--rose); font-weight: 800; }}
      .tariff.t1 {{ background: linear-gradient(160deg, var(--rose-hi), #b02a52); }}
      .tariff.t1 h3, .tariff.t1 li, .tariff.t1 li::before {{ color: #ffffff; }}
      .tariff.t1 b {{ color: #ffe3ea; }}
      .tariffs.single .tariff {{ max-width: 660px; padding: 52px 60px; }}
      .tariffs.single .tariff h3 {{ font-size: 36px; }}
      .tariffs.single .tariff b {{ margin: 22px 0 30px; font-size: 132px; }}
      .tariffs.single .tariff li {{ margin-top: 14px; padding-left: 52px; font-size: 40px; }}
      .card.calc {{ display: flex; flex-direction: column; align-items: center; justify-content: center; padding-bottom: 170px; }}
      .ghost {{ position: absolute; inset: 0; display: grid; grid-template-columns: repeat(4, 1fr);
        grid-template-rows: repeat(3, 1fr); gap: 10px; padding: 14px; opacity: 0.11; }}
      .ghost img {{ width: 100%; height: 100%; object-fit: cover; border-radius: 18px; }}
      .step {{ position: relative; text-align: center; color: var(--ink); }}
      .step.big {{ font: italic 700 140px/1.05 var(--display); }}
      .step.result {{ font: italic 700 156px/1.05 var(--display); color: var(--rose); }}
      .step.mid {{ font: 700 60px/1.25 var(--sans); color: #5c4148; }}
      .step.small {{ font: 800 38px var(--sans); letter-spacing: 0.08em; text-transform: uppercase; color: var(--rose); }}
      .stat {{ position: absolute; top: 700px; width: 440px; height: 236px; display: flex; flex-direction: column;
        align-items: center; justify-content: center; border-radius: 40px; background: rgba(255, 255, 255, 0.95);
        box-shadow: 0 18px 40px rgba(60, 20, 35, 0.25); }}
      .stat b {{ font: italic 700 120px/1 var(--display); color: var(--rose); }}
      .stat span {{ margin-top: 12px; font: 800 32px var(--sans); letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink); }}
      .tag {{ position: absolute; left: 64px; top: 486px; }}
      .tag span {{ display: inline-block; padding: 14px 26px; border-radius: 999px; background: rgba(255, 255, 255, 0.94);
        color: var(--rose); font: 800 32px var(--sans); letter-spacing: 0.08em; text-transform: uppercase;
        box-shadow: 0 8px 22px rgba(60, 20, 35, 0.18); }}
      .tag.speaker span {{ color: var(--ink); text-transform: none; letter-spacing: 0.01em; font-weight: 700; }}
      .captions-host {{ position: absolute; inset: 0; pointer-events: none; }}
      .cap {{ position: absolute; left: 0; right: 0; top: 1168px; text-align: center; }}
      .cap p {{ display: inline-block; max-width: 940px; padding: 14px 30px 16px; border-radius: 26px;
        background: rgba(42, 22, 30, 0.74); color: #ffffff; font: 800 54px/1.18 var(--sans); }}
      .cap .w {{ color: #ffffff; }}
      .end {{ position: absolute; left: 0; right: 0; top: 190px; text-align: center; }}
      .end-title {{ font: italic 700 88px/1.05 var(--display); color: var(--ink); }}
      .end-sub {{ margin-top: 18px; font: 600 40px/1.25 var(--sans); color: var(--rose); }}
      .end span, .cta span {{ display: inline-block; }}
      .cta {{ position: absolute; left: 0; right: 0; top: 1176px; text-align: center; }}
      .cta span {{ padding: 26px 56px; border-radius: 999px; color: #ffffff; font: 800 48px var(--sans);
        background: linear-gradient(90deg, var(--rose-hi), #b02a52); box-shadow: 0 16px 36px rgba(176, 42, 82, 0.4); }}
      .cta i {{ font-style: normal; margin-left: 18px; }}
      .tagline {{ position: absolute; left: 0; right: 0; top: 1392px; text-align: center; font: italic 600 46px var(--display);
        color: var(--rose); }}
      .facts {{ position: absolute; left: 0; right: 0; top: 1470px; text-align: center; font: 500 30px var(--sans);
        color: #7a5a62; letter-spacing: 0.02em; }}
      .rule {{ position: absolute; left: 470px; width: 140px; top: 1372px; height: 2px; background: var(--gold); opacity: 0.6; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="1080" data-height="1920">
      <div class="brand">LUCY SMIRNOVA</div>
      <div class="rule"></div>
      <div class="tagline">За дизайн доплачивают</div>
      <div class="facts">Онлайн-курс · 11 техник · ~5 часов практики</div>
      <div class="window" data-layout-allow-overflow>
        {footage}
      </div>
      {body}
      {audio}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      {timeline}
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("reel")
    ap.add_argument("--hook", help="build a hook variant from the beat sheet's \"hooks\" (e.g. b) for A/B tests")
    args = ap.parse_args()
    reel = args.reel

    spec = json.loads((ADS / "campaign" / "reels" / f"{reel}.json").read_text(encoding="utf-8"))
    name = reel
    if args.hook:
        # A variant changes only the opening: the headline and, optionally, the first shot. The voice stays.
        variant = spec["hooks"][args.hook]
        spec["headline"] = variant["headline"]
        if "first" in variant:
            spec["beats"][0]["clips"][0] = variant["first"]
        name = f"{reel}-{args.hook}"
    words = json.loads((ADS / "cache" / "vo" / f"{reel}.words.json").read_text(encoding="utf-8"))
    timing = Timing(words)
    p = plan(spec, timing, reel)
    cues = sfx_cues(p)
    sfx_info = copy_assets(reel, p, cues, ADS / words["audio"])
    # HyperFrames works on the project's index.html (a second root-level composition is a lint error),
    # so index.html holds the reel built last; a copy per reel is kept in the cache for reference.
    page = render_html(reel, spec, p, cues, sfx_info, words["duration"])
    out = VIDEO / "index.html"
    out.write_text(page, encoding="utf-8")
    keep = ADS / "cache" / "compositions" / f"{name}.html"
    keep.parent.mkdir(parents=True, exist_ok=True)
    keep.write_text(page, encoding="utf-8")

    print(f"{out}: {p['total']:.1f}s, {len(p['slots'])} shots, {len(p['captions'])} caption groups, "
          f"{len(cues)} sounds{' (DRAFT voice)' if words.get('draft') else ''}")
    for s in p["slots"]:
        what = s.get("clip") or s.get("photo") or (f"card:{s['card']}" if "card" in s else "grid")
        print(f"  {s['start']:6.2f}-{s['end']:6.2f}  {what:<22} {'rate ' + str(s['rate']) if 'rate' in s else ''}")


if __name__ == "__main__":
    main()
