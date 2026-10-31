"""Voice-over lines per reel, read from its campaign's scripts.md (the single source of the copy).

Every campaign is a folder ads/campaign* (ads/campaign, ads/campaign-vremya-rasti, ...) and reel codes are
numbered across campaigns, so a reel code alone finds its campaign. A reel section starts with a heading
"## R3 ..." and its voice-over is the block of "> ..." lines after "**Голос:**". Each "> " line is one phrase.
"""

from __future__ import annotations

import re
from pathlib import Path

ADS = Path(__file__).resolve().parents[1]


def campaign_dir(reel: str) -> Path:
    """The campaign folder whose beat sheets hold this reel."""
    found = sorted(ADS.glob(f"campaign*/reels/{reel}.json"))
    if not found:
        raise SystemExit(f"No ads/campaign*/reels/{reel}.json")
    return found[0].parent.parent


def reel_code(reel: str) -> str:
    """'r03' -> 'R3'."""
    return "R" + str(int(reel.lstrip("rR")))


def vo_lines(reel: str) -> list[str]:
    code = reel_code(reel)
    scripts = campaign_dir(reel) / "scripts.md"
    lines, in_reel, in_vo = [], False, False
    for raw in scripts.read_text(encoding="utf-8").splitlines():
        if raw.startswith("## "):
            in_reel = re.match(rf"## {code}\b", raw) is not None
            in_vo = False
            continue
        if not in_reel:
            continue
        if raw.startswith("**Голос:**"):
            in_vo = True
            continue
        if in_vo:
            if raw.startswith("> "):
                lines.append(raw[2:].strip())
            elif lines and raw.strip() == "":
                break
    if not lines:
        raise SystemExit(f"No voice-over for {code} in {scripts}")
    return lines


def normalize(word: str) -> str:
    return re.sub(r"[^\w-]", "", word.lower().replace("ё", "е")).strip("-")


def words(line: str) -> list[str]:
    """Words as they appear on screen (punctuation kept), dashes dropped."""
    return [w for w in line.split() if normalize(w)]
