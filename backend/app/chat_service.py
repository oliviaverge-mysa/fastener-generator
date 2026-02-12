import re
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from .mcmaster_catalog import McMasterCatalog
from cq_warehouse.fastener import (
    HexNut,
    SocketHeadCapScrew,
    HexHeadScrew,
    CounterSunkScrew,
    PanHeadScrew,
)

# ---- McMaster catalog (loaded once) ----
_HERE = os.path.dirname(__file__)
DEFAULT_CSV = os.path.join(_HERE, "data", "mcmaster_fasteners.csv")
CATALOG_PATH = os.getenv("MCMASTER_CSV_PATH", DEFAULT_CSV)
_MCM = McMasterCatalog(CATALOG_PATH)

# Map common words -> your supported families + their default standard/type
SCREW_FAMILY_RULES = [
    (re.compile(r"\bsocket\b|\bshcs\b|\bsocket head\b", re.I), "SocketHeadCapScrew", "iso4762"),
    (re.compile(r"\bhex\b|\bhex head\b|\bbolt\b", re.I), "HexHeadScrew", "iso4017"),
    (re.compile(r"\bcountersunk\b|\bflat head\b", re.I), "CounterSunkScrew", "iso10642"),
    (re.compile(r"\bpan head\b|\bpan\b", re.I), "PanHeadScrew", "iso1580"),
]

FAMILIES = {
    "HexNut": HexNut,
    "SocketHeadCapScrew": SocketHeadCapScrew,
    "HexHeadScrew": HexHeadScrew,
    "CounterSunkScrew": CounterSunkScrew,
    "PanHeadScrew": PanHeadScrew,
}

# What standards/types you want to consider "supported" for size validation.
SUPPORTED_STANDARDS_BY_FAMILY: Dict[str, List[str]] = {
    "SocketHeadCapScrew": ["iso4762"],
    "HexHeadScrew": ["iso4017"],
    "CounterSunkScrew": ["iso10642"],
    "PanHeadScrew": ["iso1580"],
    "HexNut": ["iso4032"],
}

DEFAULT_FALLBACK_SIZE = "M6-1"


@dataclass
class ParsedItem:
    part: str               # "screw" | "nut"
    family: str             # e.g. "SocketHeadCapScrew"
    fastener_type: str      # e.g. "iso4762"
    size: str               # e.g. "M6-1"
    length_mm: float | None # screws only


def _normalize_text(text: str) -> str:
    return text.strip().lower()


def _canonicalize_metric_size(major: str, pitch: str) -> str:
    """
    Normalize major/pitch strings into cq_warehouse-style size token.
    Examples:
      ("6", "1.0") -> "M6-1"
      ("2.0", "0.40") -> "M2-0.4"
    """
    major_f = float(major)
    pitch_f = float(pitch)

    major_str = str(int(major_f)) if major_f.is_integer() else str(major_f).rstrip("0").rstrip(".")
    pitch_str = str(int(pitch_f)) if pitch_f.is_integer() else str(pitch_f).rstrip("0").rstrip(".")

    return f"M{major_str}-{pitch_str}"


def _load_valid_sizes_from_cq_warehouse() -> Dict[Tuple[str, str], Set[str]]:
    """
    Build {(family, standard): set(sizes)} by querying cq_warehouse at startup.
    """
    out: Dict[Tuple[str, str], Set[str]] = {}

    for fam, standards in SUPPORTED_STANDARDS_BY_FAMILY.items():
        cls = FAMILIES.get(fam)
        if cls is None:
            continue

        for std in standards:
            sizes: Set[str] = set()
            try:
                raw = cls.sizes(std)  # type: ignore[attr-defined]
                for s in raw:
                    sizes.add(s if isinstance(s, str) else str(s))
            except Exception:
                sizes = set()

            out[(fam, std)] = sizes

    return out


_VALID_SIZES_BY_FAMILY_AND_STD: Dict[Tuple[str, str], Set[str]] = _load_valid_sizes_from_cq_warehouse()

_VALID_METRIC_SIZES_UNION: Set[str] = set()
for _k, _sizes in _VALID_SIZES_BY_FAMILY_AND_STD.items():
    _VALID_METRIC_SIZES_UNION |= _sizes

if not _VALID_METRIC_SIZES_UNION:
    _VALID_METRIC_SIZES_UNION = {DEFAULT_FALLBACK_SIZE}


def _pick_valid_metric_size_by_major(major: float, valid_sizes: Set[str]) -> Optional[str]:
    major_str = str(int(major)) if major.is_integer() else str(major).rstrip("0").rstrip(".")
    prefix = f"M{major_str}-"

    matches = [s for s in valid_sizes if s.startswith(prefix)]
    if not matches:
        return None

    def pitch_value(token: str) -> float:
        try:
            return float(token.split("-", 1)[1])
        except Exception:
            return 9999.0

    matches.sort(key=pitch_value)
    return matches[0]


def _parse_metric_thread(text: str, valid_sizes: Set[str]) -> Optional[str]:
    """
    Returns a size string like 'M6-1' or None.
    Accepts: 'M6', 'M6x1', 'M6 x 1', 'M6-1', 'm6 1.0'
    Only returns sizes that exist in valid_sizes.
    """
    m = re.search(r"\bm(\d+(?:\.\d+)?)\s*(?:x|-|\s)\s*(\d+(?:\.\d+)?)\b", text, re.I)
    if m:
        candidate = _canonicalize_metric_size(m.group(1), m.group(2))
        return candidate if candidate in valid_sizes else None

    m2 = re.search(r"\bm(\d+(?:\.\d+)?)\b", text, re.I)
    if not m2:
        return None

    major = float(m2.group(1))
    return _pick_valid_metric_size_by_major(major, valid_sizes)


def _parse_length_mm(text: str) -> Optional[float]:
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(mm|millimeter|millimeters)\b", text, re.I)
    if m:
        return float(m.group(1))

    m2 = re.search(r"\blength\s*(\d+(?:\.\d+)?)\b", text, re.I)
    if m2:
        return float(m2.group(1))

    return None


def _valid_sizes_for_item(family: str, standard: str) -> Set[str]:
    sizes = _VALID_SIZES_BY_FAMILY_AND_STD.get((family, standard), set())
    return sizes or _VALID_METRIC_SIZES_UNION


def parse_chat_message(user_text: str) -> dict:
    text = _normalize_text(user_text)

    wants_screw = "screw" in text or "bolt" in text
    wants_nut = "nut" in text
    wants_matching = "fit" in text or "matching" in text or "that fits" in text or "that will fit" in text

    # Decide screw family
    screw_family = "SocketHeadCapScrew"
    screw_type = "iso4762"
    for pattern, fam, ftype in SCREW_FAMILY_RULES:
        if pattern.search(text):
            screw_family, screw_type = fam, ftype
            break

    length_mm = _parse_length_mm(text) or 20.0

    warnings: List[str] = []
    items: List[ParsedItem] = []

    def parse_size_for(family: str, standard: str) -> str:
        valid = _valid_sizes_for_item(family, standard)
        parsed = _parse_metric_thread(text, valid)
        if parsed is not None:
            return parsed

        attempted = re.search(r"\bm(\d+(?:\.\d+)?)\s*(?:x|-|\s)\s*(\d+(?:\.\d+)?)\b", text, re.I)
        if attempted:
            attempted_token = _canonicalize_metric_size(attempted.group(1), attempted.group(2))
            warnings.append(
                f"Thread '{attempted_token}' is not supported for {family} ({standard}). "
                f"Using default {DEFAULT_FALLBACK_SIZE}."
            )
        else:
            warnings.append(f"No valid metric thread size detected. Using default {DEFAULT_FALLBACK_SIZE}.")

        valid = _valid_sizes_for_item(family, standard)
        if DEFAULT_FALLBACK_SIZE in valid:
            return DEFAULT_FALLBACK_SIZE
        pick = _pick_valid_metric_size_by_major(6.0, valid)
        return pick or DEFAULT_FALLBACK_SIZE

    if wants_screw:
        size = parse_size_for(screw_family, screw_type)
        items.append(ParsedItem(
            part="screw",
            family=screw_family,
            fastener_type=screw_type,
            size=size,
            length_mm=length_mm,
        ))

    if wants_nut:
        nut_family = "HexNut"
        nut_type = "iso4032"
        size = parse_size_for(nut_family, nut_type)
        items.append(ParsedItem(
            part="nut",
            family=nut_family,
            fastener_type=nut_type,
            size=size,
            length_mm=None,
        ))

    if not items:
        size = parse_size_for(screw_family, screw_type)
        items.append(ParsedItem(
            part="screw",
            family=screw_family,
            fastener_type=screw_type,
            size=size,
            length_mm=length_mm,
        ))

    # Friendly assistant reply (based on ParsedItem list)
    lines = ["Here’s what I understood:"]
    for it in items:
        if it.part == "screw":
            lines.append(f"- Screw: {it.family} ({it.fastener_type}), {it.size}, length {int(it.length_mm)} mm")
        else:
            lines.append(f"- Nut: {it.family} ({it.fastener_type}), {it.size}")

    if wants_nut and (wants_matching or wants_screw):
        lines.append("These will match by thread size/pitch.")

    # Resolve items to McMaster AFTER items are built
    resolved_items: List[dict] = []
    for it in items:
        item_dict = {
            "part": it.part,
            "family": it.family,
            "fastener_type": it.fastener_type,
            "size": it.size,
            "length_mm": it.length_mm,
            "simple": True,
        }

        m = _MCM.resolve_item(item_dict)
        if m:
            item_dict.update({
                "vendor": "mcmaster",
                "mcmaster_pn": m.mcmaster_pn,
                "mcmaster_url": m.url,
                "vendor_description": m.description,
                "pack_qty": m.pack_qty,
                "status": "resolved",
            })
        else:
            item_dict.update({
                "vendor": None,
                "mcmaster_pn": None,
                "mcmaster_url": None,
                "status": "needs_sourcing",
            })
            warnings.append(
                f"No McMaster mapping found for {it.part} {it.family} {it.fastener_type} {it.size}"
                + (f" L{int(it.length_mm)}" if it.length_mm else "")
            )

        resolved_items.append(item_dict)

    if warnings:
        lines.append("")
        lines.append("Notes:")
        for w in warnings:
            lines.append(f"- {w}")

    valid_metric_sizes = sorted(_VALID_METRIC_SIZES_UNION)

    return {
        "message": "\n".join(lines),
        "items": resolved_items,
        "warnings": warnings,
        "valid_metric_sizes": valid_metric_sizes,
    }
