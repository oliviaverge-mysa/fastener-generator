import re
from dataclasses import dataclass

# Map common words -> your supported families
SCREW_FAMILY_RULES = [
    (re.compile(r"\bsocket\b|\bshcs\b|\bsocket head\b", re.I), "SocketHeadCapScrew", "iso4762"),
    (re.compile(r"\bhex\b|\bhex head\b|\bbolt\b", re.I), "HexHeadScrew", "iso4017"),
    (re.compile(r"\bcountersunk\b|\bflat head\b", re.I), "CounterSunkScrew", "iso10642"),
    (re.compile(r"\bpan head\b|\bpan\b", re.I), "PanHeadScrew", "iso1580"),
]

@dataclass
class ParsedItem:
    part: str               # "screw" | "nut"
    family: str             # e.g. "SocketHeadCapScrew"
    fastener_type: str      # e.g. "iso4762"
    size: str               # e.g. "M6-1"
    length_mm: float | None # screws only


def _normalize_text(text: str) -> str:
    return text.strip().lower()


def _parse_metric_thread(text: str) -> str | None:
    """
    Returns size string like 'M6-1' or None.
    Accepts: 'M6', 'M6x1', 'M6 x 1', 'M6-1', 'm6 1.0'
    """
    # M6x1 / M6 x 1 / M6-1 / M6 1
    m = re.search(r"\bm(\d+(?:\.\d+)?)\s*(?:x|-|\s)?\s*(\d+(?:\.\d+)?)\b", text, re.I)
    if m:
        major = m.group(1)
        pitch = m.group(2)
        # normalize like M6-1 or M6-1.25
        return f"M{major}-{pitch}".replace(".0", "")

    # M6 only (unknown pitch): default coarse pitch for common sizes (basic)
    m2 = re.search(r"\bm(\d+(?:\.\d+)?)\b", text, re.I)
    if not m2:
        return None

    major = float(m2.group(1))
    coarse_pitch_map = {
        3.0: 0.5,
        4.0: 0.7,
        5.0: 0.8,
        6.0: 1.0,
        8.0: 1.25,
        10.0: 1.5,
        12.0: 1.75,
    }
    pitch = coarse_pitch_map.get(major)
    if pitch is None:
        # fallback: keep major and assume 1.0 (better than nothing)
        pitch = 1.0
    major_str = str(int(major)) if major.is_integer() else str(major)
    pitch_str = str(int(pitch)) if float(pitch).is_integer() else str(pitch)
    return f"M{major_str}-{pitch_str}".replace(".0", "")


def _parse_length_mm(text: str) -> float | None:
    """
    Looks for length like '20mm', '20 mm', 'length 20', '20 millimeters'
    """
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(mm|millimeter|millimeters)\b", text, re.I)
    if m:
        return float(m.group(1))

    m2 = re.search(r"\blength\s*(\d+(?:\.\d+)?)\b", text, re.I)
    if m2:
        return float(m2.group(1))

    return None


def parse_chat_message(user_text: str) -> dict:
    """
    Returns a structured response your frontend can display + use.
    """
    text = _normalize_text(user_text)

    wants_screw = "screw" in text or "bolt" in text
    wants_nut = "nut" in text
    wants_matching = "fit" in text or "matching" in text or "that fits" in text or "that will fit" in text

    size = _parse_metric_thread(text) or "M6-1"
    length_mm = _parse_length_mm(text) or 20.0

    # Decide screw family
    screw_family = "SocketHeadCapScrew"
    screw_type = "iso4762"
    for pattern, fam, ftype in SCREW_FAMILY_RULES:
        if pattern.search(text):
            screw_family, screw_type = fam, ftype
            break

    items: list[ParsedItem] = []

    if wants_screw:
        items.append(ParsedItem(
            part="screw",
            family=screw_family,
            fastener_type=screw_type,
            size=size,
            length_mm=length_mm,
        ))

    if wants_nut:
        items.append(ParsedItem(
            part="nut",
            family="HexNut",
            fastener_type="iso4032",
            size=size,
            length_mm=None,
        ))

    if not items:
        # If user didn't say screw/nut explicitly, guess screw.
        items.append(ParsedItem(
            part="screw",
            family=screw_family,
            fastener_type=screw_type,
            size=size,
            length_mm=length_mm,
        ))

    # Build a friendly assistant reply
    lines = ["Here’s what I understood:"]
    for it in items:
        if it.part == "screw":
            lines.append(f"- Screw: {it.family} ({it.fastener_type}), {it.size}, length {int(it.length_mm)} mm")
        else:
            lines.append(f"- Nut: {it.family} ({it.fastener_type}), {it.size}")

    if wants_nut and (wants_matching or wants_screw):
        lines.append("These will match by thread size/pitch.")

    return {
        "message": "\n".join(lines),
        "items": [
            {
                "part": it.part,
                "family": it.family,
                "fastener_type": it.fastener_type,
                "size": it.size,
                "length_mm": it.length_mm,
                "simple": True,
            }
            for it in items
        ],
    }
