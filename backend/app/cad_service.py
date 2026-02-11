import io
import os
import zipfile
import tempfile
from dataclasses import dataclass
import cadquery as cq
from cadquery import exporters

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
    part: str
    family: str
    fastener_type: str
    size: str
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
        return cls(size=req.size, fastener_type=req.fastener_type, simple=req.simple)

    if req.part == "screw":
        if req.length_mm is None:
            raise ValueError("length_mm is required for screws")

        return cls(
            size=req.size,
            length=req.length_mm * MM,
            fastener_type=req.fastener_type,
            simple=req.simple,
        )

    raise ValueError("part must be 'screw' or 'nut'")


def generate_step_and_stl_zip(req: GenerateRequest) -> bytes:
    solid = _build_solid(req)

    # STEP export often requires a real file path (not BytesIO),
    # so we export to a temporary directory.
    with tempfile.TemporaryDirectory() as tmpdir:
        step_path = os.path.join(tmpdir, "part.step")
        stl_path = os.path.join(tmpdir, "part.stl")

        exporters.export(solid, step_path, exporters.ExportTypes.STEP)
        exporters.export(solid, stl_path, exporters.ExportTypes.STL)

        with open(step_path, "rb") as f:
            step_bytes = f.read()
        with open(stl_path, "rb") as f:
            stl_bytes = f.read()

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("part.step", step_bytes)
        zf.writestr("part.stl", stl_bytes)

    return zip_buf.getvalue()
