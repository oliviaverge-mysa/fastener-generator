from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Callable

import cadquery as cq

from OCP.gp import gp_Dir, gp_Ax2, gp_Pnt
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.TopoDS import TopoDS_Shape
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_QuasiUniformDeflection


Point2D = Tuple[float, float]
Polyline2D = List[Point2D]


@dataclass(frozen=True)
class Projection2D:
    visible: List[Polyline2D]
    hidden: List[Polyline2D]


def _to_topods(shape) -> TopoDS_Shape:
    """
    Convert CadQuery objects into TopoDS_Shape.
    """
    if isinstance(shape, cq.Workplane):
        return shape.val().wrapped
    if hasattr(shape, "wrapped"):  # cq.Shape
        return shape.wrapped
    if hasattr(shape, "val"):      # cq_warehouse objects often
        v = shape.val()
        return v.wrapped if hasattr(v, "wrapped") else v
    return shape  # assume already TopoDS_Shape


def _get_edge_caster() -> Callable:
    """
    Different OCP builds expose casting helpers in different places.
    We detect them once, then use the returned function.
    """
    # 1) Most common in some builds: OCP.TopoDS.topods.Edge(...)
    try:
        from OCP.TopoDS import topods  # type: ignore
        return lambda shp: topods.Edge(shp)
    except Exception:
        pass

    # 2) Some builds: OCP.TopoDS.topods_Edge(shp)
    try:
        from OCP.TopoDS import topods_Edge  # type: ignore
        return lambda shp: topods_Edge(shp)
    except Exception:
        pass

    # 3) Some builds: TopoDS_Edge.DownCast(...)
    try:
        from OCP.TopoDS import TopoDS_Edge  # type: ignore
        return lambda shp: TopoDS_Edge.DownCast(shp)
    except Exception:
        pass

    raise ImportError(
        "Could not find an OCP TopoDS edge cast helper. "
        "Tried: topods.Edge, topods_Edge, TopoDS_Edge.DownCast"
    )


_EDGE_CAST = _get_edge_caster()


def _edges_to_polylines(edges_shape: TopoDS_Shape, deflection: float = 0.10) -> List[Polyline2D]:
    out: List[Polyline2D] = []
    exp = TopExp_Explorer(edges_shape, TopAbs_EDGE)

    while exp.More():
        edge = _EDGE_CAST(exp.Current())
        if edge is None:
            exp.Next()
            continue

        c = BRepAdaptor_Curve(edge)
        discret = GCPnts_QuasiUniformDeflection(c, deflection)
        if discret.IsDone() and discret.NbPoints() >= 2:
            pts: Polyline2D = []
            for i in range(1, discret.NbPoints() + 1):
                p = discret.Value(i)  # gp_Pnt
                pts.append((float(p.X()), float(p.Y())))
            out.append(pts)

        exp.Next()

    return out


def project_shape_hlr(
    shape,
    view_dir: Tuple[float, float, float],
    up_dir: Tuple[float, float, float],
    deflection: float = 0.10,
) -> Projection2D:
    """
    True orthographic projection using OpenCascade HLR.
    Produces visible & hidden polylines in 2D.
    """
    topo = _to_topods(shape)

    vdir = gp_Dir(*view_dir)
    xdir = gp_Dir(*up_dir)  # must not be parallel to vdir
    ax2 = gp_Ax2(gp_Pnt(0, 0, 0), vdir, xdir)

    projector = HLRAlgo_Projector(ax2)

    algo = HLRBRep_Algo()
    algo.Add(topo)
    algo.Projector(projector)
    algo.Update()
    algo.Hide()
    algo.Update()

    hlr = HLRBRep_HLRToShape(algo)

    vis = hlr.VCompound()
    hid = hlr.HCompound()

    visible_polys = _edges_to_polylines(vis, deflection=deflection)
    hidden_polys = _edges_to_polylines(hid, deflection=deflection)

    return Projection2D(visible=visible_polys, hidden=hidden_polys)
