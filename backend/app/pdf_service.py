import io
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cad_service import GenerateRequest


# ----------------------------
# Existing spec sheet (keep)
# ----------------------------
def generate_spec_sheet_pdf(req: "GenerateRequest", vendor: dict | None = None) -> bytes:
    if vendor:
        rows.insert(0, ("Vendor", vendor.get("vendor", "—")))
        rows.insert(1, ("McMaster PN", vendor.get("mcmaster_pn", "—")))
        rows.insert(2, ("McMaster URL", vendor.get("mcmaster_url", "—")))
    
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    W, H = letter

    margin = 18 * mm
    y = H - margin

    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, y, "FASTENER DRAWING / SPEC SHEET")
    y -= 10 * mm

    c.setFont("Helvetica", 11)
    c.setFillGray(0.25)
    c.drawString(margin, y, "Generated automatically (v1)")
    c.setFillGray(0.0)
    y -= 12 * mm

    part_name = "Screw" if req.part == "screw" else "Nut"
    length_str = f"{int(req.length_mm)} mm" if (req.part == "screw" and req.length_mm is not None) else "—"
    callout = f"{part_name} — {req.family} — {req.size} — {length_str} — {req.fastener_type.upper()}"
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "CALLOUT:")
    c.setFont("Helvetica", 12)
    c.drawString(margin + 22 * mm, y, callout)
    y -= 14 * mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "SPECS:")
    y -= 8 * mm

    rows = [
        ("Vendor", vendor.get("vendor") if vendor else "—"),
        ("McMaster PN", vendor.get("mcmaster_pn") if vendor else "—"),
        ("McMaster URL", vendor.get("mcmaster_url") if vendor else "—"),
        ("Part", req.part),
        ("Family", req.family),
        ("Standard / Type", req.fastener_type),
        ("Thread size", req.size),
        ("Length", length_str),
        ("Simplified geometry", "Yes" if req.simple else "No"),
        ("Generated", datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]


    table_x = margin
    table_y_top = y
    row_h = 8 * mm
    col1_w = 40 * mm
    col2_w = 120 * mm
    table_w = col1_w + col2_w
    table_h = row_h * len(rows)

    c.setLineWidth(1)
    c.rect(table_x, table_y_top - table_h, table_w, table_h)
    c.line(table_x + col1_w, table_y_top, table_x + col1_w, table_y_top - table_h)

    c.setFont("Helvetica", 11)
    y_row = table_y_top - row_h + 2.5 * mm
    for k, v in rows:
        c.setFillGray(0.15)
        c.drawString(table_x + 3 * mm, y_row, str(k))
        c.setFillGray(0.0)
        c.drawString(table_x + col1_w + 3 * mm, y_row, str(v))
        y_row -= row_h
        if y_row > table_y_top - table_h:
            c.line(table_x, y_row + (row_h - 2.5 * mm), table_x + table_w, y_row + (row_h - 2.5 * mm))

    y = table_y_top - table_h - 14 * mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "NOTES:")
    y -= 7 * mm
    c.setFont("Helvetica", 11)
    notes = [
        "1) Geometry generated programmatically. Not a certified standards drawing.",
        "2) Dimensions shown are based on input parameters; verify for manufacturing use.",
        "3) Add true orthographic views & GD&T in a later version if required.",
    ]
    for n in notes:
        c.drawString(margin, y, n)
        y -= 6 * mm

    c.setLineWidth(1)
    c.line(margin, margin + 18 * mm, W - margin, margin + 18 * mm)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, margin + 12 * mm, "Project:")
    c.setFont("Helvetica", 10)
    c.drawString(margin + 18 * mm, margin + 12 * mm, "Fastener Finder")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(W - margin - 60 * mm, margin + 12 * mm, "File:")
    c.setFont("Helvetica", 10)
    c.drawString(W - margin - 44 * mm, margin + 12 * mm, "spec_sheet.pdf")

    c.showPage()
    c.save()
    return buf.getvalue()


# ----------------------------
# True drawing (new)
# ----------------------------
def _bounds(polys):
    xs, ys = [], []
    for pl in polys:
        for x, y in pl:
            xs.append(x); ys.append(y)
    if not xs:
        return (0, 0, 1, 1)
    return (min(xs), min(ys), max(xs), max(ys))


def _fit_transform(bounds, box):
    xmin, ymin, xmax, ymax = bounds
    bx, by, bw, bh = box
    mw = max(xmax - xmin, 1e-9)
    mh = max(ymax - ymin, 1e-9)

    pad = 4 * mm
    bw2 = max(bw - 2 * pad, 1)
    bh2 = max(bh - 2 * pad, 1)

    s = min(bw2 / mw, bh2 / mh)
    tx = bx + bw / 2 - s * (xmin + mw / 2)
    ty = by + bh / 2 - s * (ymin + mh / 2)
    return s, tx, ty


def _draw_polylines(c, polys, s, tx, ty):
    for pl in polys:
        if len(pl) < 2:
            continue
        x0, y0 = pl[0]
        c.moveTo(tx + s * x0, ty + s * y0)
        for x, y in pl[1:]:
            c.lineTo(tx + s * x, ty + s * y)
        c.stroke()


def _draw_view(c, proj, box, title):
    bx, by, bw, bh = box
    c.setLineWidth(0.8)
    c.rect(bx, by, bw, bh)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(bx + 3 * mm, by + bh - 6 * mm, title)

    all_polys = proj.visible + proj.hidden
    b = _bounds(all_polys)
    s, tx, ty = _fit_transform(b, box)

    # hidden
    c.saveState()
    c.setLineWidth(0.35)
    c.setDash(3, 2)
    _draw_polylines(c, proj.hidden, s, tx, ty)
    c.restoreState()

    # visible
    c.setLineWidth(0.9)
    c.setDash()
    _draw_polylines(c, proj.visible, s, tx, ty)


def generate_drawing_pdf(req: "GenerateRequest", shape, vendor: dict | None = None) -> bytes:
    """
    True orthographic drawing via HLR (front/right/top).
    Lazy-import projection to avoid crashing the whole backend on startup.
    """
    from .projection_service import project_shape_hlr  # ✅ lazy import

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A4))
    W, H = landscape(A4)

    margin = 10 * mm
    c.setLineWidth(1)
    c.rect(margin, margin, W - 2 * margin, H - 2 * margin)

    # Title block
    tb_h = 30 * mm
    c.setLineWidth(0.8)
    c.rect(margin, margin, W - 2 * margin, tb_h)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin + 3 * mm, margin + tb_h - 8 * mm, "FASTENER DRAWING (TRUE VIEWS)")
    c.setFont("Helvetica", 9)
    c.drawString(margin + 3 * mm, margin + tb_h - 16 * mm, f"{req.family}  {req.size}  {req.fastener_type}")
    if vendor and vendor.get("mcmaster_pn"):
        c.drawString(margin + 3 * mm, margin + tb_h - 22 * mm, f"McMaster: {vendor.get('mcmaster_pn')}  {vendor.get('mcmaster_url')}")

    c.drawString(margin + 3 * mm, margin + 6 * mm, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # View area
    top_y = margin + tb_h + 6 * mm
    top_h = H - top_y - margin
    gap = 6 * mm

    vw = (W - 2 * margin - 2 * gap) / 3
    vh = top_h

    boxes = [
        (margin, top_y, vw, vh),
        (margin + vw + gap, top_y, vw, vh),
        (margin + 2 * (vw + gap), top_y, vw, vh),
    ]

    # Projections
    # Front: look along +Y (XZ plane)
    front = project_shape_hlr(shape, view_dir=(0, 1, 0), up_dir=(0, 0, 1), deflection=0.10)
    # Right: look along +X (YZ plane)
    right = project_shape_hlr(shape, view_dir=(1, 0, 0), up_dir=(0, 0, 1), deflection=0.10)
    # Top: look along +Z (XY plane)
    top = project_shape_hlr(shape, view_dir=(0, 0, 1), up_dir=(0, 1, 0), deflection=0.10)

    _draw_view(c, front, boxes[0], "FRONT VIEW")
    _draw_view(c, right, boxes[1], "RIGHT VIEW")
    _draw_view(c, top, boxes[2], "TOP VIEW")

    c.showPage()
    c.save()
    return buf.getvalue()
