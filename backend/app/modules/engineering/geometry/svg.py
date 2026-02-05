from __future__ import annotations

from typing import Iterable

import ezdxf

from app.modules.engineering.geometry.dxf_ops import _entity_segments
from app.modules.engineering.geometry.validate import Segment2D


def _all_segments(doc: ezdxf.EzDxf) -> list[Segment2D]:
    msp = doc.modelspace()
    segs: list[Segment2D] = []
    for e in msp:
        segs.extend(_entity_segments(e))
    return segs


def dxf_to_svg_preview(doc: ezdxf.EzDxf) -> str:
    segs = _all_segments(doc)
    if not segs:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"></svg>'
    xs = [p[0] for s in segs for p in s]
    ys = [p[1] for s in segs for p in s]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    pad = max(max_x - min_x, max_y - min_y) * 0.05 or 10.0
    min_x -= pad
    max_x += pad
    min_y -= pad
    max_y += pad
    width = max_x - min_x
    height = max_y - min_y

    def _map_point(x: float, y: float) -> tuple[float, float]:
        sx = x - min_x
        sy = max_y - y
        return (sx, sy)

    lines: list[str] = []
    for (x1, y1), (x2, y2) in segs:
        ax1, ay1 = _map_point(float(x1), float(y1))
        ax2, ay2 = _map_point(float(x2), float(y2))
        lines.append(
            f'<line x1="{ax1:.3f}" y1="{ay1:.3f}" x2="{ax2:.3f}" y2="{ay2:.3f}" stroke="#111" stroke-width="1" />'
        )
    body = "".join(lines)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.3f} {height:.3f}">{body}</svg>'
