from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .cad_service import GenerateRequest, generate_step_and_stl_zip, FAMILIES
from cq_warehouse.fastener import HexNut, Screw, Nut  # used for discovery

app = FastAPI(title="Fastener Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateBody(BaseModel):
    part: str = Field(..., description="screw | nut")
    family: str = Field(..., description="Family class name, e.g. SocketHeadCapScrew, HexNut")
    fastener_type: str = Field(..., description="Standard type id, e.g. iso4762, iso4032")
    size: str = Field(..., description="Size string, e.g. M6-1 or #6-32")
    length_mm: float | None = Field(None, description="Required for screws")
    simple: bool = Field(True, description="If true, do not model helical threads (faster)")

@app.get("/api/catalog")
def catalog():
    """
    Gives the frontend enough info to build dropdowns.
    cq_warehouse exposes helpers like .types() and .sizes(type). :contentReference[oaicite:2]{index=2}
    """
    families = sorted(list(FAMILIES.keys()))

    # Provide common options (you can expand this with more families/standards later)
    return {
        "families": families,
        "examples": {
            "nut": {"family": "HexNut", "fastener_type": "iso4032", "size": "M6-1"},
            "screw": {"family": "SocketHeadCapScrew", "fastener_type": "iso4762", "size": "M6-1", "length_mm": 20},
        }
    }

@app.post("/api/generate")
def generate(body: GenerateBody):
    try:
        req = GenerateRequest(
            part=body.part,
            family=body.family,
            fastener_type=body.fastener_type,
            size=body.size,
            length_mm=body.length_mm,
            simple=body.simple,
        )
        zip_bytes = generate_step_and_stl_zip(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=fastener.zip"},
    )
