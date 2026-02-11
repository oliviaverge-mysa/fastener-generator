import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

from .cad_service import GenerateRequest

def generate_drawing_pdf(req: GenerateRequest) -> bytes:
    """
    Simple v1 “engineering sheet” PDF:
    - Title block
    - Part callout
    - Key specs table
    - Notes
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    W, H = letter

    # Layout constants
    margin = 18 * mm
    y = H - margin

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, y, "FASTENER DRAWING / SPEC SHEET")
    y -= 10 * mm

    c.setFont("Helvetica", 11)
    c.setFillGray(0.25)
    c.drawString(margin, y, "Generated automatically (v1)")
    c.setFillGray(0.0)
    y -= 12 * mm

    # Callout line (looks like an engineering callout)
    part_name = "Screw" if req.part == "screw" else "Nut"
    length_str = f"{int(req.length_mm)} mm" if (req.part == "screw" and req.length_mm is not None) else "—"
    callout = f"{part_name} — {req.family} — {req.size} — {length_str} — {req.fastener_type.upper()}"
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "CALLOUT:")
    c.setFont("Helvetica", 12)
    c.drawString(margin + 22 * mm, y, callout)
    y -= 14 * mm

    # Specs table (simple)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "SPECS:")
    y -= 8 * mm

    rows = [
        ("Part", req.part),
        ("Family", req.family),
        ("Standard / Type", req.fastener_type),
        ("Thread size", req.size),
        ("Length", length_str),
        ("Simplified geometry", "Yes" if req.simple else "No"),
        ("Generated", datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]

    # Draw table box
    table_x = margin
    table_y_top = y
    row_h = 8 * mm
    col1_w = 40 * mm
    col2_w = 120 * mm
    table_w = col1_w + col2_w
    table_h = row_h * len(rows)

    c.setLineWidth(1)
    c.rect(table_x, table_y_top - table_h, table_w, table_h)

    # Vertical divider
    c.line(table_x + col1_w, table_y_top, table_x + col1_w, table_y_top - table_h)

    # Rows
    c.setFont("Helvetica", 11)
    y_row = table_y_top - row_h + 2.5 * mm
    for k, v in rows:
        c.setFillGray(0.15)
        c.drawString(table_x + 3 * mm, y_row, str(k))
        c.setFillGray(0.0)
        c.drawString(table_x + col1_w + 3 * mm, y_row, str(v))
        y_row -= row_h
        # horizontal line (except after last)
        if y_row > table_y_top - table_h:
            c.line(table_x, y_row + (row_h - 2.5 * mm), table_x + table_w, y_row + (row_h - 2.5 * mm))

    y = table_y_top - table_h - 14 * mm

    # Notes
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

    # Footer / title block-ish line
    c.setLineWidth(1)
    c.line(margin, margin + 18 * mm, W - margin, margin + 18 * mm)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, margin + 12 * mm, "Project:")
    c.setFont("Helvetica", 10)
    c.drawString(margin + 18 * mm, margin + 12 * mm, "Fastener Finder")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(W - margin - 60 * mm, margin + 12 * mm, "File:")
    c.setFont("Helvetica", 10)
    c.drawString(W - margin - 44 * mm, margin + 12 * mm, "drawing.pdf")

    c.showPage()
    c.save()
    return buf.getvalue()
