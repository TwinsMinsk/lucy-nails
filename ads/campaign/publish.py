"""Push the campaign into the admin "Реклама" section of the site and pull the team's uploads back.

    $env:ADS_SYNC_TOKEN = "<the ADS_SYNC_TOKEN of the Backend service>"
    python ads/campaign/publish.py                                  -> https://api.lucysmirnova.ru/api
    python ads/campaign/publish.py --api http://127.0.0.1:8000/api  -> local backend
    python ads/campaign/publish.py --dry-run                        -> show what would be sent
    python ads/campaign/publish.py --campaign ads/campaign-vremya-rasti   -> another campaign

Texts come from the campaign folder (ads/campaign unless --campaign says otherwise): scripts.md, captions.md,
calendar.md, about.md, admin.json and reels/<reel>.json, the same sources as build_page.py; files are the
renders in ads/out (the final `<reel>.mp4` when it exists, otherwise the draft). Only files whose sha256
changed are uploaded. Voice recordings and other files the team uploaded in the admin are downloaded to
ads/vo/inbox/<reel>/, and the comments are printed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parent
ADS = CAMPAIGN.parent
sys.path.insert(0, str(CAMPAIGN))
from build_page import calendar_rows, layers, reel_data  # noqa: E402

DEFAULT_API = "https://api.lucysmirnova.ru/api"
MSK = timezone(timedelta(hours=3))
INBOX = ADS / "vo" / "inbox"


class Api:
    def __init__(self, base: str, token: str):
        self.base = base.rstrip("/")
        self.token = token

    def call(self, method: str, path: str, *, payload=None, upload: Path | None = None, params=None):
        url = f"{self.base}{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
        headers = {"X-Ads-Token": self.token}
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode()
            headers["Content-Type"] = "application/json"
        handle = None
        if upload is not None:
            handle = upload.open("rb")
            data = handle
            headers["Content-Type"] = "application/octet-stream"
            headers["Content-Length"] = str(upload.stat().st_size)
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            sys.exit(f"{method} {path}: HTTP {exc.code} {detail}")
        finally:
            if handle:
                handle.close()
        return json.loads(body) if body else None

    def download(self, path: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        partial = dest.with_name(dest.name + ".partial")
        with urllib.request.urlopen(f"{self.base}{path}", timeout=600) as response, partial.open("wb") as out:
            while chunk := response.read(1 << 20):
                out.write(chunk)
        partial.replace(dest)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def render(reel: str, name: str) -> Path:
    """The final render when it exists, otherwise the draft."""
    out = ADS / "out" / reel
    final = out / name.replace("{v}", "")
    return final if final.exists() else out / name.replace("{v}", "-draft")


def about_sections(folder: Path) -> list[dict]:
    text = (folder / "about.md").read_text(encoding="utf-8")
    sections = []
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        title, _, body = block.partition("\n")
        sections.append({"title": title.strip(), "body": body.strip()})
    return sections


def calendar_entries(rows: list[dict], start: date, time: str) -> list[dict]:
    entries = []
    for index, row in enumerate(rows):
        day, month = map(int, re.search(r"(\d{1,2})\.(\d{1,2})", row["day"]).groups())
        when = date(start.year + (month < start.month), month, day)
        # The reel this entry is about: the one with its «title», else the first one mentioned.
        named = re.search(r"R(\d+) «", row["what"]) or re.search(r"R(\d+)", row["what"])
        entries.append({
            "key": f"w{row['week']}-{when.isoformat()}",
            "day": when.isoformat(),
            "time": time,
            "week": row["week"],
            "title": row["what"],
            "note": None if row["stories"] in ("", "—") else row["stories"],
            "material_code": f"r{int(named.group(1)):02d}" if named else None,
            "order_index": index,
        })
    return entries


def build(folder: Path, config: dict) -> tuple[dict, dict[str, list[dict]]]:
    scripts = (folder / "scripts.md").read_text(encoding="utf-8")
    captions = (folder / "captions.md").read_text(encoding="utf-8")
    layout = layers(config)
    group_of = {reel: key for key, _, _, reels in layout for reel in reels}
    materials, files = [], {}
    for index, reel in enumerate((reel for *_, reels in layout for reel in reels), start=1):
        d = reel_data(reel, scripts, captions)
        base = d["utm"] or reel
        materials.append({
            "code": reel,
            "kind": "reel",
            "title": d["title"],
            "group_key": group_of.get(reel),
            "hook": d["hook"],
            "voiceover": "\n".join(d["vo"]),
            "caption": d["caption"],
            "link_url": config["stories_link"].format(utm=d["utm"]) if d["utm"] else None,
            "utm_content": d["utm"] or None,
            "duration_seconds": d["seconds"],
            "order_index": index,
        })
        reel_files = [
            {"key": "video", "role": "video", "path": render(reel, f"{reel}{{v}}.mp4"), "filename": f"{base}.mp4"},
            {"key": "cover", "role": "cover", "path": render(reel, f"{reel}{{v}}-cover.jpg"), "filename": f"{base}-cover.jpg"},
        ]
        for hook in d["hooks"][1:] if reel in config["hook_reels"] else []:
            label = " ".join(hook["lines"])
            for role, suffix in (("video", ".mp4"), ("cover", "-cover.jpg")):
                reel_files.append({
                    "key": f"{role}-{hook['id']}",
                    "role": role,
                    "variant": hook["id"],
                    "label": label,
                    "path": ADS / "out" / reel / f"{reel}-hook-{hook['id']}{suffix}",
                    "filename": f"{base}-{hook['id']}{suffix}",
                })
        files[reel] = [f for f in reel_files if f["path"].exists()]

    start = date.fromisoformat(config["starts_on"])
    rows = calendar_rows((folder / "calendar.md").read_text(encoding="utf-8"))
    payload = {
        "title": config["title"],
        "summary": config["summary"],
        "status": config["status"],
        "starts_on": config["starts_on"],
        "groups": [{"key": key, "title": title, "note": note} for key, title, note, _ in layout],
        "about": about_sections(folder),
        "materials": materials,
        "tasks": [dict(task, order_index=i) for i, task in enumerate(config["tasks"], start=1)],
        "calendar": calendar_entries(rows, start, config["post_time"]),
    }
    return payload, files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--campaign", type=Path, default=CAMPAIGN, help="campaign folder (default: ads/campaign)")
    parser.add_argument("--api", default=os.environ.get("ADS_API_URL", DEFAULT_API))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--prune", action="store_true", help="delete reels and tasks missing from the sources")
    args = parser.parse_args()

    config = json.loads((args.campaign / "admin.json").read_text(encoding="utf-8"))
    payload, files = build(args.campaign, config)
    payload["prune"] = args.prune
    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        for reel, items in files.items():
            print(reel, *(f"{f['key']}={f['path'].name}" for f in items))
        return

    token = os.environ.get("ADS_SYNC_TOKEN", "")
    if len(token) < 32:
        sys.exit("Set ADS_SYNC_TOKEN (the same value as on the Backend service)")
    api = Api(args.api, token)
    slug = config["slug"]
    state = api.call("PUT", f"/internal/ads/campaigns/{slug}", payload=payload)
    print(f"Campaign «{state['title']}»: {len(state['materials'])} materials, {len(state['calendar'])} calendar entries")

    uploaded = removed = 0
    for material in state["materials"]:
        code = material["code"]
        remote = {f["key"]: f for f in material["files"] if f["uploaded_by"] is None}
        local = {f["key"]: f for f in files.get(code, [])}
        for key, item in local.items():
            if remote.get(key, {}).get("sha256") == sha256(item["path"]):
                continue
            params = {"role": item["role"], "filename": item["filename"]}
            params.update({k: item[k] for k in ("variant", "label") if item.get(k)})
            size = item["path"].stat().st_size / 1e6
            print(f"  {code} {key}: {item['path'].name} ({size:.1f} MB)")
            api.call("PUT", f"/internal/ads/campaigns/{slug}/materials/{code}/files/{key}", upload=item["path"], params=params)
            uploaded += 1
        for key in remote.keys() - local.keys():
            print(f"  {code} {key}: removed")
            api.call("DELETE", f"/internal/ads/campaigns/{slug}/materials/{code}/files/{key}")
            removed += 1
    print(f"Files: {uploaded} uploaded, {removed} removed, the rest unchanged")

    pulled = 0
    for material in state["materials"]:
        for f in material["files"]:
            if f["uploaded_by"] is None:
                continue
            dest = INBOX / material["code"] / f"{f['created_at'][:10]}-{f['id'][:8]}-{f['filename']}"
            if dest.exists() and dest.stat().st_size == f["size_bytes"]:
                continue
            api.download(f["download_url"], dest)
            print(f"  ← {material['code']} {f['filename']} from {f['uploaded_by']['name']} -> {dest.relative_to(ADS.parent)}")
            pulled += 1
    if pulled:
        print(f"Team uploads: {pulled} new file(s) in {INBOX.relative_to(ADS.parent)}")

    codes = {m["id"]: m["code"].upper() for m in state["materials"]}
    if state["comments"]:
        print("Comments:")
        for c in state["comments"]:
            where = codes.get(c["material_id"], "кампания")
            author = c["author"]["name"] if c["author"] else "?"
            when = datetime.fromisoformat(c["created_at"]).replace(tzinfo=timezone.utc).astimezone(MSK)
            print(f"  [{when:%d.%m %H:%M}] {author} · {where}: {c['body']}")


if __name__ == "__main__":
    main()
