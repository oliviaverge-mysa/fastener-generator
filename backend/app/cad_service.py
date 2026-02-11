import io
import zipfile
from dataclasses import dataclass
import cadquery as cq
from cadquery import exporters

# cq_warehouse provides parametric fasteners (nuts/screws/washers)
# including size catalogs and standards like iso4032, iso4762, etc.
from cq_warehouse.fastener import (
    HexNut,
    SocketHeadCapScrew,
    HexHeadScrew,
    CounterSunkScrew,
    PanHeadScrew,
)

MM = 1.0

@dataclass(frozen=True)
class GenerateRequest:
    part: str              # "screw" | "nut"
    family: str            # e.g. "SocketHeadCapScrew" | "HexHeadScrew" | "HexNut"
    fastener_type: str     # e.g. "iso4762" | "iso4017" | "iso4032"
    size: str              # e.g. "M6-1" | "M3-0.5"
    length_mm: float | None
    simple: bool


FAMILIES = {
    "HexNut": HexNut,
    "SocketHeadCapScrew": SocketHeadCapScrew,
    "HexHeadScrew": HexHeadScrew,
    "CounterSunkScrew": CounterSunkScrew,
    "PanHeadScrew": PanHeadScrew,
}

def _build_solid(req: GenerateRequest) -> cq.Solid:
    if req.family not in FAMILIES:
        raise ValueError(f"Unsupported family: {req.family}")

    cls = FAMILIES[req.family]

    if req.part == "nut":
        # Nut interface: Nut(size, fastener_type, hand='right', simple=True)
        solid = cls(size=req.size, fastener_type=req.fastener_type, simple=req.simple)
        return solid

    if req.part == "screw":
        if req.length_mm is None:
            raise ValueError("length_mm is required for screws")

        # Screw interface: Screw(size, length, fastener_type, hand='right', simple=True, ...)
        solid = cls(
            size=req.size,
            length=req.length_mm * MM,
            fastener_type=req.fastener_type,
            simple=req.simple,
        )
        return solid

    raise ValueError("part must be 'screw' or 'nut'")


def generate_step_and_stl_zip(req: GenerateRequest) -> bytes:
    solid = _build_solid(req)

    # Export to in-memory buffers
    step_buf = io.BytesIO()
    stl_buf = io.BytesIO()

    # CadQuery exporters can write to file-like objects
    exporters.export(solid, step_buf, exporters.ExportTypes.STEP)
    exporters.export(solid, stl_buf, exporters.ExportTypes.STL)

    step_bytes = step_buf.getvalue()
    stl_bytes = stl_buf.getvalue()

    # Package into a zip
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("part.step", step_bytes)
        zf.writestr("part.stl", stl_bytes)

    return zip_buf.getvalue()
