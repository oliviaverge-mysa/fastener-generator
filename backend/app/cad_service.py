import io
import os
import zipfile
import tempfile
from dataclasses import dataclass
from .mcmaster_catalog import McMasterCatalog


import cadquery as cq
from cadquery import exporters

from .pdf_service import generate_drawing_pdf
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

# ---- McMaster catalog (loaded once) ----
CATALOG_PATH = os.getenv("MCMASTER_CSV_PATH", "backend/data/mcmaster_fasteners.csv")
_MCM = McMasterCatalog(CATALOG_PATH)



def _build_shape(req: GenerateRequest):
    """
    Returns a CADQuery shape/object that exporters can write.
    cq_warehouse fasteners are usually CQ shapes/parts that exporters can handle directly.
    """
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


def _export_step_stl_bytes(req: GenerateRequest) -> tuple[bytes, bytes]:
    """
    Export STEP + STL to bytes using temp files (most reliable with cadquery exporters).
    """
    shape = _build_shape(req)

    with tempfile.TemporaryDirectory() as td:
        step_path = os.path.join(td, "model.step")
        stl_path = os.path.join(td, "model.stl")

        # Exporters expect a CQ object/shape; cq_warehouse fasteners typically work here.
        exporters.export(shape, step_path)
        exporters.export(shape, stl_path)

        with open(step_path, "rb") as f:
            step_bytes = f.read()
        with open(stl_path, "rb") as f:
            stl_bytes = f.read()

    return step_bytes, stl_bytes


def generate_step_and_stl_zip(req: GenerateRequest) -> bytes:
    """
    Returns a ZIP containing:
    - model.step
    - model.stl
    - drawing.pdf (true views) OR spec_sheet.pdf fallback
    """
    # Build shape once (used for drawing)
    shape = _build_shape(req)

    # Export CAD
    step_bytes, stl_bytes = _export_step_stl_bytes(req)

    # PDFs: prefer true drawing, fall back to spec sheet
    from .pdf_service import generate_drawing_pdf, generate_spec_sheet_pdf

    vendor = None
    item_dict = {
        "part": req.part,
        "family": req.family,
        "fastener_type": req.fastener_type,
        "size": req.size,
        "length_mm": req.length_mm,
    }
    m = _MCM.resolve_item(item_dict)
    if m:
        vendor = {
            "vendor": "mcmaster",
            "mcmaster_pn": m.mcmaster_pn,
            "mcmaster_url": m.url,
            "vendor_description": m.description,
            "pack_qty": m.pack_qty,
        }

    try:
        pdf_bytes = generate_drawing_pdf(req, shape, vendor=vendor)
        pdf_name = "drawing.pdf"
    except Exception:
        pdf_bytes = generate_spec_sheet_pdf(req, vendor=vendor)
        pdf_name = "spec_sheet.pdf"


    # Package into zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("model.step", step_bytes)
        zf.writestr("model.stl", stl_bytes)
        zf.writestr(pdf_name, pdf_bytes)

    return buf.getvalue()



# cad_service.py (add near your other helpers)

def _as_cq_shape(obj):
    """
    Try hard to get a CadQuery Shape from cq_warehouse objects.
    """
    # Many CQ objects support .val()
    if hasattr(obj, "val"):
        try:
            return obj.val()
        except Exception:
            pass

    # Some have .solid()
    if hasattr(obj, "solid"):
        try:
            return obj.solid().val() if hasattr(obj.solid(), "val") else obj.solid()
        except Exception:
            pass

    # Might already be a Shape
    return obj


def _bbox_mm(shape) -> dict:
    s = _as_cq_shape(shape)
    bb = s.BoundingBox()
    return {
        "x_mm": float(bb.xlen),
        "y_mm": float(bb.ylen),
        "z_mm": float(bb.zlen),
        "xmin": float(bb.xmin),
        "xmax": float(bb.xmax),
        "ymin": float(bb.ymin),
        "ymax": float(bb.ymax),
        "zmin": float(bb.zmin),
        "zmax": float(bb.zmax),
    }
