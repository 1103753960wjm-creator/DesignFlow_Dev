from __future__ import annotations

import ezdxf
from ezdxf.entities import DXFEntity, Line, LWPolyline, Polyline
from ezdxf.layouts import Modelspace

from app.modules.engineering.schemas import CADActionType, CADModificationCommand
from app.modules.engineering.geometry.validate import Segment2D, find_colinear_overlaps


def _entity_segments(entity: DXFEntity) -> list[Segment2D]:
    dxftype = entity.dxftype()
    if dxftype == "LINE":
        e = entity  # type: ignore[assignment]
        line: Line = e
        p1 = (float(line.dxf.start.x), float(line.dxf.start.y))
        p2 = (float(line.dxf.end.x), float(line.dxf.end.y))
        return [(p1, p2)]
    if dxftype == "LWPOLYLINE":
        e = entity  # type: ignore[assignment]
        pl: LWPolyline = e
        pts = [(float(p[0]), float(p[1])) for p in pl.get_points("xy")]
        if len(pts) < 2:
            return []
        segs: list[Segment2D] = []
        for i in range(len(pts) - 1):
            segs.append((pts[i], pts[i + 1]))
        if bool(pl.closed) and len(pts) >= 3:
            segs.append((pts[-1], pts[0]))
        return segs
    if dxftype == "POLYLINE":
        e = entity  # type: ignore[assignment]
        pl2: Polyline = e
        pts = [(float(v.dxf.location.x), float(v.dxf.location.y)) for v in pl2.vertices()]
        if len(pts) < 2:
            return []
        segs = [((pts[i][0], pts[i][1]), (pts[i + 1][0], pts[i + 1][1])) for i in range(len(pts) - 1)]
        if bool(pl2.is_closed) and len(pts) >= 3:
            segs.append((pts[-1], pts[0]))
        return segs
    return []


def _all_segments(msp: Modelspace, *, exclude_handles: set[str] | None = None) -> list[Segment2D]:
    segs: list[Segment2D] = []
    for e in msp:
        if exclude_handles and str(getattr(e.dxf, "handle", "")).upper() in exclude_handles:
            continue
        segs.extend(_entity_segments(e))
    return segs


def _translate_entity(entity: DXFEntity, dx: float, dy: float) -> None:
    dxftype = entity.dxftype()
    if dxftype == "LINE":
        line: Line = entity  # type: ignore[assignment]
        line.dxf.start = (float(line.dxf.start.x) + dx, float(line.dxf.start.y) + dy, float(line.dxf.start.z))
        line.dxf.end = (float(line.dxf.end.x) + dx, float(line.dxf.end.y) + dy, float(line.dxf.end.z))
        return
    if dxftype == "LWPOLYLINE":
        pl: LWPolyline = entity  # type: ignore[assignment]
        points = pl.get_points("xyseb")
        moved = []
        for x, y, s, e, b in points:
            moved.append((float(x) + dx, float(y) + dy, s, e, b))
        pl.set_points(moved, format="xyseb")
        return
    if dxftype == "POLYLINE":
        pl2: Polyline = entity  # type: ignore[assignment]
        for v in pl2.vertices():
            v.dxf.location = (float(v.dxf.location.x) + dx, float(v.dxf.location.y) + dy, float(v.dxf.location.z))
        return
    raise ValueError(f"不支持的实体类型: {dxftype}")


def _delete_entity(entity: DXFEntity) -> None:
    layout = entity.get_layout()
    if layout is None:
        entity.destroy()
        return
    layout.delete_entity(entity)


def _resize_room(entity: DXFEntity, *, axis: str, new_value_mm: float) -> None:
    if new_value_mm <= 0:
        raise ValueError("value 必须为正数")
    dxftype = entity.dxftype()
    if dxftype not in ("LWPOLYLINE", "POLYLINE"):
        raise ValueError("RESIZE_ROOM 仅支持 POLYLINE/LWPOLYLINE")
    segs = _entity_segments(entity)
    if not segs:
        raise ValueError("目标实体为空")
    xs = [p[0] for s in segs for p in s]
    ys = [p[1] for s in segs for p in s]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    cur_w = max_x - min_x
    cur_h = max_y - min_y
    if axis == "x":
        if cur_w <= 0:
            raise ValueError("当前宽度非法")
        sx, sy = new_value_mm / cur_w, 1.0
    else:
        if cur_h <= 0:
            raise ValueError("当前高度非法")
        sx, sy = 1.0, new_value_mm / cur_h

    def _scale_point(p: tuple[float, float]) -> tuple[float, float]:
        x, y = p
        return (cx + (x - cx) * sx, cy + (y - cy) * sy)

    if dxftype == "LWPOLYLINE":
        pl: LWPolyline = entity  # type: ignore[assignment]
        points = pl.get_points("xyseb")
        scaled = []
        for x, y, s, e, b in points:
            nx, ny = _scale_point((float(x), float(y)))
            scaled.append((nx, ny, s, e, b))
        pl.set_points(scaled, format="xyseb")
        return
    pl2: Polyline = entity  # type: ignore[assignment]
    for v in pl2.vertices():
        nx, ny = _scale_point((float(v.dxf.location.x), float(v.dxf.location.y)))
        v.dxf.location = (nx, ny, float(v.dxf.location.z))


def _select_targets(msp: Modelspace, target_description: str) -> list[DXFEntity]:
    desc = (target_description or "").strip()
    if not desc:
        return []
    if "墙" in desc or "wall" in desc.lower():
        walls = [e for e in msp if str(getattr(e.dxf, "layer", "")).upper() == "WALL"]
        if not walls:
            return []
        lowered = desc.lower()
        want_north = ("北" in desc) or ("north" in lowered)
        want_south = ("南" in desc) or ("south" in lowered)
        want_east = ("东" in desc) or ("east" in lowered)
        want_west = ("西" in desc) or ("west" in lowered)
        if not any([want_north, want_south, want_east, want_west]):
            return walls

        def _entity_mid(entity: DXFEntity) -> tuple[float, float] | None:
            segs = _entity_segments(entity)
            if not segs:
                return None
            xs = [p[0] for s in segs for p in s]
            ys = [p[1] for s in segs for p in s]
            return ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)

        mids: list[tuple[DXFEntity, float, float]] = []
        for e in walls:
            mid = _entity_mid(e)
            if mid is None:
                continue
            mids.append((e, mid[0], mid[1]))
        if not mids:
            return walls
        xs = [x for _, x, _ in mids]
        ys = [y for _, _, y in mids]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        tol_x = max((max_x - min_x) * 0.02, 1e-6)
        tol_y = max((max_y - min_y) * 0.02, 1e-6)

        selected: list[DXFEntity] = []
        for e, x, y in mids:
            if want_north and (max_y - y) <= tol_y:
                selected.append(e)
            elif want_south and (y - min_y) <= tol_y:
                selected.append(e)
            elif want_east and (max_x - x) <= tol_x:
                selected.append(e)
            elif want_west and (x - min_x) <= tol_x:
                selected.append(e)
        return selected or walls
    return list(msp)


def apply_cad_command(doc: ezdxf.EzDxf, cmd: CADModificationCommand) -> None:
    msp = doc.modelspace()
    targets = _select_targets(msp, cmd.target_description)
    if not targets:
        raise ValueError("未找到匹配的目标实体")

    if cmd.action_type == CADActionType.DELETE_ITEM:
        for e in targets:
            _delete_entity(e)
        return

    if cmd.action_type == CADActionType.RESIZE_ROOM:
        axis = cmd.axis or "x"
        if cmd.value is None:
            raise ValueError("RESIZE_ROOM 需要 value")
        for e in targets:
            _resize_room(e, axis=axis, new_value_mm=float(cmd.value))
        return

    if cmd.action_type == CADActionType.MOVE_WALL:
        dx = float(cmd.delta_x if cmd.delta_x is not None else (cmd.value or 0.0))
        dy = float(cmd.delta_y if cmd.delta_y is not None else 0.0)
        if dx == 0.0 and dy == 0.0:
            raise ValueError("MOVE_WALL 需要 delta_x/delta_y")
        moved_before: list[Segment2D] = []
        moved_after: list[Segment2D] = []
        exclude_handles = {str(getattr(e.dxf, "handle", "")).upper() for e in targets}
        for e in targets:
            moved_before.extend(_entity_segments(e))
            _translate_entity(e, dx, dy)
            moved_after.extend(_entity_segments(e))
        if moved_before and moved_after:
            other_segments = _all_segments(msp, exclude_handles=exclude_handles)
            violations = find_colinear_overlaps(moved_after, other_segments)
            if violations:
                raise ValueError("墙体移动后发生重叠")
        return

    raise ValueError(f"不支持的操作类型: {cmd.action_type}")
