from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from shapely.geometry import LineString


Point2D = tuple[float, float]
Segment2D = tuple[Point2D, Point2D]


@dataclass(frozen=True)
class OverlapViolation:
    moved_segment: Segment2D
    overlapped_segment: Segment2D
    overlap_length: float


def _to_linestring(seg: Segment2D) -> LineString:
    (x1, y1), (x2, y2) = seg
    return LineString([(float(x1), float(y1)), (float(x2), float(y2))])


def find_colinear_overlaps(
    moved_segments: Iterable[Segment2D],
    other_segments: Iterable[Segment2D],
    *,
    min_overlap_length: float = 1e-3,
) -> list[OverlapViolation]:
    violations: list[OverlapViolation] = []
    moved_list = list(moved_segments)
    other_list = list(other_segments)
    moved = [_to_linestring(s) for s in moved_list]
    others = [_to_linestring(s) for s in other_list]
    for m_idx, m in enumerate(moved):
        for o_idx, o in enumerate(others):
            inter = m.intersection(o)
            if inter.is_empty:
                continue
            if inter.geom_type in ("LineString", "MultiLineString") and float(inter.length) >= min_overlap_length:
                violations.append(
                    OverlapViolation(
                        moved_segment=moved_list[m_idx],
                        overlapped_segment=other_list[o_idx],
                        overlap_length=float(inter.length),
                    )
                )
    return violations
