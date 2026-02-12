# backend/mcmaster_catalog.py
from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional


# ---- Normalization maps (tune to your org) ----

FAMILY_TO_KIND = {
    "SocketHeadCapScrew": "shcs",
    "HexHeadScrew": "hex",
    "CounterSunkScrew": "csk",
    "PanHeadScrew": "pan",
    "HexNut": "hexnut",
}

# You can also map standards if you treat some as equivalent for purchasing
STANDARD_MAP = {
    "iso4762": "iso4762",
    "iso4017": "iso4017",
    "iso10642": "iso10642",
    "iso1580": "iso1580",
    "iso4032": "iso4032",
}

def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s.strip().lower())

def _norm_size(size: str) -> str:
    # cq_warehouse uses M6-1 style; convert M6x1 -> M6-1 if needed
    t = _norm(size)
    t = t.replace("×", "x")
    t = re.sub(r"^m(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)$", r"m\1-\2", t)
    return t.upper()  # keep cq_warehouse style like "M6-1"

def build_spec_key(item: Dict[str, Any]) -> str:
    """
    Build a deterministic key from your existing payload fields.
    Item shape is what parse_chat_message returns for each item.
    """
    part = _norm(item["part"])           # screw|nut
    family = item["family"]
    ftype = _norm(item["fastener_type"])
    size = _norm_size(item["size"])
    length = item.get("length_mm")

    kind = FAMILY_TO_KIND.get(family, _norm(family))
    std = STANDARD_MAP.get(ftype, ftype)

    if part == "screw":
        L = int(round(float(length))) if length is not None else 0
        return f"{part}|{kind}|{std}|{size}|L{L}"
    else:
        return f"{part}|{kind}|{std}|{size}"

@dataclass(frozen=True)
class McMasterMatch:
    spec_key: str
    mcmaster_pn: str
    description: str = ""
    pack_qty: Optional[int] = None

    @property
    def url(self) -> str:
        return f"https://www.mcmaster.com/{self.mcmaster_pn}/"

class McMasterCatalog:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.by_key: Dict[str, McMasterMatch] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.csv_path):
            # empty catalog is fine; resolver will just not find matches
            self.by_key = {}
            return

        by_key: Dict[str, McMasterMatch] = {}
        with open(self.csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = _norm(row["spec_key"])
                pn = row["mcmaster_pn"].strip()
                desc = row.get("description", "").strip()
                pack = row.get("pack_qty", "").strip()
                by_key[key] = McMasterMatch(
                    spec_key=row["spec_key"],
                    mcmaster_pn=pn,
                    description=desc,
                    pack_qty=int(pack) if pack else None,
                )
        self.by_key = by_key

    def resolve_item(self, item: Dict[str, Any]) -> Optional[McMasterMatch]:
        key = _norm(build_spec_key(item))
        return self.by_key.get(key)
