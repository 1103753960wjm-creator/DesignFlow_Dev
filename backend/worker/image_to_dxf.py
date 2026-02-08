import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


def _ensure_deps():
    try:
        import cv2
        import numpy
        import ezdxf
        return
    except Exception:
        raise RuntimeError("缺少依赖：opencv-python-headless / numpy / ezdxf")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "")
    if raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "y", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "")
    if raw == "":
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "")
    if raw == "":
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _odd_kernel(k: int) -> int:
    k = max(1, int(k))
    if k % 2 == 0:
        k += 1
    return k


@dataclass(frozen=True)
class DetectParams:
    blur_kernel: int
    morph_close: bool
    morph_kernel: int
    canny_low: int
    canny_high: int
    hough_threshold: int
    min_line: int
    max_gap: int


class ImageToDxfError(RuntimeError):
    pass


class ImageClarityError(ImageToDxfError):
    pass


def _remove_small_and_thin_components(mask, *, min_area: int, thin_px: int, long_px: int):
    import cv2
    import numpy as np

    if mask is None or mask.size == 0:
        return mask

    keep = mask.copy()
    num, labels, stats, _ = cv2.connectedComponentsWithStats(keep, connectivity=8)
    for i in range(1, num):
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        w = int(stats[i, cv2.CC_STAT_WIDTH])
        h = int(stats[i, cv2.CC_STAT_HEIGHT])
        area = int(stats[i, cv2.CC_STAT_AREA])

        if area < min_area:
            keep[labels == i] = 0
            continue

        if min(w, h) <= thin_px and max(w, h) >= long_px:
            keep[labels == i] = 0
            continue

    return keep


def _detect_and_crop_frame(gray, mask, *, margin_px: int):
    import cv2
    import numpy as np

    h, w = gray.shape[:2]
    if w < 32 or h < 32:
        return gray, mask, 0, 0

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return gray, mask, 0, 0

    c = max(contours, key=cv2.contourArea)
    area = float(cv2.contourArea(c))
    if area < 0.15 * float(w * h):
        return gray, mask, 0, 0

    x, y, bw, bh = cv2.boundingRect(c)
    if bw <= 0 or bh <= 0:
        return gray, mask, 0, 0

    x0 = max(0, x + margin_px)
    y0 = max(0, y + margin_px)
    x1 = min(w, x + bw - margin_px)
    y1 = min(h, y + bh - margin_px)
    if (x1 - x0) < 32 or (y1 - y0) < 32:
        return gray, mask, 0, 0

    return gray[y0:y1, x0:x1], mask[y0:y1, x0:x1], x0, y0


def _merge_lines_pairwise(
    lines,
    *,
    angle_tol_deg: float,
    dist_tol_px: float,
    gap_tol_px: float,
    min_len_px: float,
):
    import numpy as np

    segs = lines.reshape(-1, 4).astype(np.float64)
    p1 = segs[:, 0:2]
    p2 = segs[:, 2:4]
    d = p2 - p1
    lens = np.linalg.norm(d, axis=1)
    keep = lens > max(1e-6, min_len_px * 0.25)
    p1 = p1[keep]
    p2 = p2[keep]
    lens = lens[keep]
    if p1.size == 0:
        return np.zeros((0, 4), dtype=np.float64)

    u = (p2 - p1) / lens[:, None]
    ang = np.degrees(np.arctan2(u[:, 1], u[:, 0]))
    ang = (ang + 180.0) % 180.0

    n = p1.shape[0]
    parent = np.arange(n, dtype=np.int32)
    rank = np.zeros(n, dtype=np.int32)

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int):
        ra = find(a)
        rb = find(b)
        if ra == rb:
            return
        if rank[ra] < rank[rb]:
            parent[ra] = rb
        elif rank[ra] > rank[rb]:
            parent[rb] = ra
        else:
            parent[rb] = ra
            rank[ra] += 1

    def angle_diff(a: float, b: float) -> float:
        d = abs(a - b)
        return min(d, 180.0 - d)

    def pt_line_dist(pt: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
        ab = b - a
        denom = np.linalg.norm(ab)
        if denom < 1e-6:
            return float(np.linalg.norm(pt - a))
        ap = pt - a
        cross = float(ab[0] * ap[1] - ab[1] * ap[0])
        return abs(cross) / float(denom)

    for i in range(n):
        for j in range(i + 1, n):
            if angle_diff(float(ang[i]), float(ang[j])) > angle_tol_deg:
                continue

            min_d = min(
                pt_line_dist(p1[i], p1[j], p2[j]),
                pt_line_dist(p2[i], p1[j], p2[j]),
                pt_line_dist(p1[j], p1[i], p2[i]),
                pt_line_dist(p2[j], p1[i], p2[i]),
            )
            if min_d > dist_tol_px:
                continue

            ui = u[i]
            uj = u[j]
            if (ui @ uj) < 0:
                uj = -uj
            u_mean = ui + uj
            nrm = np.linalg.norm(u_mean)
            if nrm < 1e-6:
                u_mean = ui
            else:
                u_mean /= nrm

            t_i = np.array([(p1[i] @ u_mean), (p2[i] @ u_mean)])
            t_j = np.array([(p1[j] @ u_mean), (p2[j] @ u_mean)])
            a0, a1 = float(t_i.min()), float(t_i.max())
            b0, b1 = float(t_j.min()), float(t_j.max())
            gap = max(0.0, max(a0, b0) - min(a1, b1))
            if gap > gap_tol_px:
                continue

            union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        r = find(i)
        groups.setdefault(r, []).append(i)

    merged: list[list[float]] = []
    for idxs in groups.values():
        if not idxs:
            continue
        idxs_arr = np.asarray(idxs, dtype=np.int32)

        u_ref = u[idxs_arr[0]].copy()
        aligned = u[idxs_arr].copy()
        flip = (aligned @ u_ref) < 0
        aligned[flip] *= -1.0
        u_mean = aligned.mean(axis=0)
        nrm = np.linalg.norm(u_mean)
        if nrm < 1e-6:
            u_mean = u_ref
        else:
            u_mean /= nrm

        normal = np.array([-u_mean[1], u_mean[0]], dtype=np.float64)
        mids = (p1[idxs_arr] + p2[idxs_arr]) * 0.5
        rho = float((mids @ normal).mean())
        p0 = normal * rho

        t1 = (p1[idxs_arr] - p0) @ u_mean
        t2 = (p2[idxs_arr] - p0) @ u_mean
        tmin = float(min(t1.min(), t2.min()))
        tmax = float(max(t1.max(), t2.max()))
        if (tmax - tmin) < min_len_px:
            continue

        s = p0 + u_mean * tmin
        e = p0 + u_mean * tmax
        merged.append([float(s[0]), float(s[1]), float(e[0]), float(e[1])])

    if not merged:
        return np.zeros((0, 4), dtype=np.float64)

    out = np.asarray(merged, dtype=np.float64)
    key = np.round(out / 2.0).astype(int)
    _, uniq_idx = np.unique(key, axis=0, return_index=True)
    return out[np.sort(uniq_idx)]


def _orthogonalize_lines(segs, *, tol_deg: float):
    import numpy as np

    out = segs.astype(np.float64).copy()
    for i in range(out.shape[0]):
        x1, y1, x2, y2 = out[i]
        dx = x2 - x1
        dy = y2 - y1
        ang = abs(np.degrees(np.arctan2(dy, dx)))
        ang = ang % 180.0
        if ang > 90.0:
            ang = 180.0 - ang

        if ang <= tol_deg:
            y = (y1 + y2) * 0.5
            out[i] = [x1, y, x2, y]
        elif abs(90.0 - ang) <= tol_deg:
            x = (x1 + x2) * 0.5
            out[i] = [x, y1, x, y2]
    return out


def _run_canny_hough(gray, *, params: DetectParams):
    import cv2
    import numpy as np

    blur_k = _odd_kernel(params.blur_kernel)
    blur = cv2.GaussianBlur(gray, (blur_k, blur_k), 0)

    use_binarize = _env_bool("IMAGE_DXF_BINARIZE", True)
    if use_binarize:
        block = _odd_kernel(_env_int("IMAGE_DXF_ADAPTIVE_BLOCK", 35))
        c = _env_int("IMAGE_DXF_ADAPTIVE_C", 10)
        mask = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, block, c)
    else:
        _, mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    fg_ratio = float((mask > 0).mean())
    if fg_ratio < 0.0005 or fg_ratio > 0.5:
        _, mask2 = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        fg_ratio2 = float((mask2 > 0).mean())
        if 0.0005 <= fg_ratio2 <= 0.5:
            mask = mask2

    if params.morph_close:
        mk = _odd_kernel(params.morph_kernel)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (mk, mk))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    min_area = _env_int("IMAGE_DXF_CC_MIN_AREA", 50)
    thin_px = _env_int("IMAGE_DXF_CC_THIN_PX", 4)
    long_px = _env_int("IMAGE_DXF_CC_LONG_PX", 250)
    if _env_bool("IMAGE_DXF_FILTER_COMPONENTS", True):
        mask = _remove_small_and_thin_components(mask, min_area=min_area, thin_px=thin_px, long_px=long_px)

    edges = cv2.Canny(mask, int(params.canny_low), int(params.canny_high))
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180.0,
        threshold=int(params.hough_threshold),
        minLineLength=int(params.min_line),
        maxLineGap=int(params.max_gap),
    )
    return mask, edges, lines


def _save_debug_images(*, out_dir: Path, gray, edges, color, lines) -> None:
    import cv2

    out_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_dir / "debug_01_gray.png"), gray)
    cv2.imwrite(str(out_dir / "debug_02_edges.png"), edges)

    canvas = color.copy()
    if lines is not None:
        for (x1, y1, x2, y2) in lines.reshape(-1, 4):
            cv2.line(canvas, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
    cv2.imwrite(str(out_dir / "debug_03_lines.png"), canvas)


def image_to_dxf(*, image_path: str | Path, dxf_path: str | Path) -> Path:
    _ensure_deps()
    import cv2

    img_path = Path(image_path)
    out_path = Path(dxf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    color = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
    if color is None:
        raise ImageToDxfError(f"无法读取图片: {img_path}")
    gray = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
    full_h = int(gray.shape[0])

    crop = _env_bool("IMAGE_DXF_CROP_FRAME", True)
    crop_margin = _env_int("IMAGE_DXF_CROP_MARGIN", 24)
    if crop:
        blur_k0 = _odd_kernel(_env_int("IMAGE_DXF_BLUR_KERNEL", 3))
        blur0 = cv2.GaussianBlur(gray, (blur_k0, blur_k0), 0)
        block0 = _odd_kernel(_env_int("IMAGE_DXF_ADAPTIVE_BLOCK", 35))
        c0 = _env_int("IMAGE_DXF_ADAPTIVE_C", 10)
        mask0 = cv2.adaptiveThreshold(blur0, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, block0, c0)
        if _env_bool("IMAGE_DXF_MORPH_CLOSE", True):
            mk0 = _odd_kernel(_env_int("IMAGE_DXF_MORPH_KERNEL", 3))
            kernel0 = cv2.getStructuringElement(cv2.MORPH_RECT, (mk0, mk0))
            mask0 = cv2.morphologyEx(mask0, cv2.MORPH_CLOSE, kernel0)
        gray2, _, off_x, off_y = _detect_and_crop_frame(gray, mask0, margin_px=crop_margin)
        if (off_x or off_y) or (gray2.shape != gray.shape):
            hh, ww = gray2.shape[:2]
            gray = gray2
            color = color[off_y : off_y + hh, off_x : off_x + ww]
    else:
        off_x, off_y = 0, 0

    params = DetectParams(
        blur_kernel=_env_int("IMAGE_DXF_BLUR_KERNEL", 3),
        morph_close=_env_bool("IMAGE_DXF_MORPH_CLOSE", True),
        morph_kernel=_env_int("IMAGE_DXF_MORPH_KERNEL", 3),
        canny_low=_env_int("IMAGE_DXF_CANNY_LOW", 25),
        canny_high=_env_int("IMAGE_DXF_CANNY_HIGH", 75),
        hough_threshold=_env_int("IMAGE_DXF_HOUGH_THRESHOLD", 25),
        min_line=_env_int("IMAGE_DXF_MIN_LINE", 10),
        max_gap=_env_int("IMAGE_DXF_MAX_GAP", 25),
    )

    mask, edges, lines = _run_canny_hough(gray, params=params)
    raw_count = 0 if lines is None else int(lines.reshape(-1, 4).shape[0])

    min_ok = _env_int("IMAGE_DXF_MIN_RAW_LINES", 5)
    if raw_count < min_ok:
        print("[WARN] Initial detection low. Retrying with aggressive parameters...")
        aggressive = DetectParams(
            blur_kernel=params.blur_kernel,
            morph_close=params.morph_close,
            morph_kernel=params.morph_kernel,
            canny_low=_env_int("IMAGE_DXF_CANNY_LOW_AGG", 10),
            canny_high=_env_int("IMAGE_DXF_CANNY_HIGH_AGG", 50),
            hough_threshold=_env_int("IMAGE_DXF_HOUGH_THRESHOLD_AGG", 15),
            min_line=_env_int("IMAGE_DXF_MIN_LINE_AGG", max(6, params.min_line // 2)),
            max_gap=_env_int("IMAGE_DXF_MAX_GAP_AGG", max(35, params.max_gap)),
        )
        mask2, edges2, lines2 = _run_canny_hough(gray, params=aggressive)
        raw_count2 = 0 if lines2 is None else int(lines2.reshape(-1, 4).shape[0])
        if raw_count2 > raw_count:
            mask, edges, lines, raw_count = mask2, edges2, lines2, raw_count2

    max_ok = _env_int("IMAGE_DXF_MAX_RAW_LINES", 800)
    if raw_count > max_ok:
        print("[WARN] Initial detection too noisy. Retrying with stricter parameters...")
        strict = DetectParams(
            blur_kernel=_env_int("IMAGE_DXF_BLUR_KERNEL_STRICT", max(5, params.blur_kernel)),
            morph_close=_env_bool("IMAGE_DXF_MORPH_CLOSE_STRICT", params.morph_close),
            morph_kernel=_env_int("IMAGE_DXF_MORPH_KERNEL_STRICT", params.morph_kernel),
            canny_low=_env_int("IMAGE_DXF_CANNY_LOW_STRICT", 40),
            canny_high=_env_int("IMAGE_DXF_CANNY_HIGH_STRICT", 120),
            hough_threshold=_env_int("IMAGE_DXF_HOUGH_THRESHOLD_STRICT", 70),
            min_line=_env_int("IMAGE_DXF_MIN_LINE_STRICT", 60),
            max_gap=_env_int("IMAGE_DXF_MAX_GAP_STRICT", 12),
        )
        mask3, edges3, lines3 = _run_canny_hough(gray, params=strict)
        raw_count3 = 0 if lines3 is None else int(lines3.reshape(-1, 4).shape[0])
        if 0 < raw_count3 < raw_count:
            mask, edges, lines, raw_count = mask3, edges3, lines3, raw_count3

    fallback_contour = _env_bool("IMAGE_DXF_FALLBACK_CONTOUR", True)
    fallback_contours = []
    if raw_count == 0 and fallback_contour:
        import cv2

        fallback_contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not fallback_contours:
            inv = cv2.bitwise_not(mask)
            fallback_contours, _ = cv2.findContours(inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not fallback_contours:
            blur_k = _odd_kernel(params.blur_kernel)
            blur = cv2.GaussianBlur(gray, (blur_k, blur_k), 0)
            _, b1 = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            fallback_contours, _ = cv2.findContours(b1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not fallback_contours:
                b2 = cv2.bitwise_not(b1)
                fallback_contours, _ = cv2.findContours(b2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not fallback_contours:
            raise ImageClarityError("未检测到可用线条")
    elif raw_count == 0:
        raise ImageClarityError("未检测到可用线条")

    debug = _env_bool("IMAGE_DXF_DEBUG", False)
    if debug:
        debug_dir = os.getenv("IMAGE_DXF_DEBUG_DIR", "").strip()
        out_dir = Path(debug_dir) if debug_dir else img_path.parent
        _save_debug_images(out_dir=out_dir, gray=gray, edges=edges, color=color, lines=lines)

    h = full_h
    mm_per_px = _env_float("IMAGE_DXF_MM_PER_PX", 10.0)

    import ezdxf
    doc = ezdxf.new(dxfversion="R2010")
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    if not doc.layers.has_entry("WALL"):
        doc.layers.new(name="WALL")

    if lines is not None and raw_count > 0:
        angle_tol = _env_float("IMAGE_DXF_MERGE_ANGLE_TOL", 5.0)
        dist_tol = _env_float("IMAGE_DXF_MERGE_DIST_TOL", 10.0)
        gap_tol = _env_float("IMAGE_DXF_MERGE_GAP_TOL", float(params.max_gap))
        min_merged = _env_float("IMAGE_DXF_MIN_MERGED_LINE_PX", float(params.min_line))
        do_merge = _env_bool("IMAGE_DXF_MERGE", True)

        segs = (
            _merge_lines_pairwise(
                lines,
                angle_tol_deg=angle_tol,
                dist_tol_px=dist_tol,
                gap_tol_px=gap_tol,
                min_len_px=min_merged,
            )
            if do_merge
            else lines.reshape(-1, 4).astype("float64")
        )

        do_ortho = _env_bool("IMAGE_DXF_ORTHO", True)
        ortho_tol = _env_float("IMAGE_DXF_ORTHO_TOL", 5.0)
        if do_ortho and segs.size:
            segs = _orthogonalize_lines(segs, tol_deg=ortho_tol)

        merged_count = int(segs.shape[0])
        min_merged_ok = _env_int("IMAGE_DXF_MIN_MERGED_LINES", 4)
        if merged_count < min_merged_ok:
            raise ImageClarityError("线条数量不足，疑似图片清晰度不足")

        for (x1, y1, x2, y2) in segs:
            x1o = float(x1) + float(off_x)
            y1o = float(y1) + float(off_y)
            x2o = float(x2) + float(off_x)
            y2o = float(y2) + float(off_y)
            sx = float(x1o) * mm_per_px
            sy = float(h - float(y1o)) * mm_per_px
            ex = float(x2o) * mm_per_px
            ey = float(h - float(y2o)) * mm_per_px
            msp.add_line((sx, sy), (ex, ey), dxfattribs={"layer": "WALL"})
    elif fallback_contours:
        import cv2

        img_area = float(gray.shape[0] * gray.shape[1])
        keep = [c for c in fallback_contours if float(cv2.contourArea(c)) >= max(200.0, img_area * 0.002)]
        if not keep:
            raise ImageClarityError("线条数量不足，疑似图片清晰度不足")
        keep.sort(key=cv2.contourArea, reverse=True)
        eps = float(_env_float("IMAGE_DXF_CONTOUR_EPS", 2.5))
        max_cnt = int(_env_int("IMAGE_DXF_CONTOUR_MAX", 10))
        as_lines = _env_bool("IMAGE_DXF_CONTOUR_AS_LINES", True)
        for c in keep[:max_cnt]:
            approx = cv2.approxPolyDP(c, epsilon=eps, closed=True)
            pts = [(float(p[0][0]) + float(off_x), float(p[0][1]) + float(off_y)) for p in approx]
            if len(pts) < 3:
                continue
            mapped = [(x * mm_per_px, (h - y) * mm_per_px) for x, y in pts]
            msp.add_lwpolyline(mapped, format="xy", close=True, dxfattribs={"layer": "WALL"})
            if as_lines:
                n = int(len(mapped))
                for i in range(n):
                    x1, y1 = mapped[i]
                    x2, y2 = mapped[(i + 1) % n]
                    msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "WALL"})
    else:
        raise ImageClarityError("未检测到可用线条")
    doc.saveas(str(out_path))
    return out_path


def _ensure_layer(doc, name: str) -> None:
    if not doc.layers.has_entry(name):
        doc.layers.new(name=name)


def _ensure_unit_square_block(doc, name: str) -> None:
    if name in doc.blocks:
        return
    blk = doc.blocks.new(name=name)
    blk.add_lwpolyline([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)], format="xy", close=True)


def _add_solid_hatch(msp, points, *, layer: str) -> None:
    hatch = msp.add_hatch(dxfattribs={"layer": layer})
    if hasattr(hatch, "set_solid_fill"):
        hatch.set_solid_fill(color=7)
    else:
        hatch.dxf.solid_fill = 1
        hatch.dxf.pattern_name = "SOLID"
    hatch.paths.add_polyline_path(points, is_closed=True)


def _dxf_from_class_map(*, class_map, h: int, w: int, mm_per_px: float, out_path: Path) -> Path:
    _ensure_deps()
    import cv2
    import numpy as np
    import ezdxf

    if class_map.shape[:2] != (h, w):
        raise ImageToDxfError("Segmentation output size mismatch")

    doc = ezdxf.new(dxfversion="R2010")
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()

    _ensure_layer(doc, "WALL")
    _ensure_layer(doc, "WINDOW")
    _ensure_layer(doc, "DOOR")
    _ensure_unit_square_block(doc, "WINDOW")
    _ensure_unit_square_block(doc, "DOOR")

    wall_mask = (class_map == 1).astype(np.uint8) * 255
    if wall_mask.max() == 0:
        raise ImageClarityError("Segmentation detected no WALL pixels")

    close_k = _odd_kernel(_env_int("IMAGE_DXF_WALL_CLOSE_KERNEL", 7))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (close_k, close_k))
    wall_mask = cv2.morphologyEx(wall_mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(wall_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ImageClarityError("Segmentation detected no WALL contours")

    min_area_px = float(_env_float("IMAGE_DXF_WALL_MIN_AREA_PX", 800.0))
    kept = [c for c in contours if float(cv2.contourArea(c)) >= min_area_px]
    if not kept:
        raise ImageClarityError("Segmentation WALL contours too small")

    for c in kept:
        peri = float(cv2.arcLength(c, True))
        eps = float(_env_float("IMAGE_DXF_WALL_EPS_FRAC", 0.01)) * peri
        approx = cv2.approxPolyDP(c, epsilon=eps, closed=True)
        pts_px = [(float(p[0][0]), float(p[0][1])) for p in approx]
        if len(pts_px) < 3:
            continue
        pts_mm = [(x * mm_per_px, (float(h) - y) * mm_per_px) for x, y in pts_px]
        msp.add_lwpolyline(pts_mm, format="xy", close=True, dxfattribs={"layer": "WALL"})
        _add_solid_hatch(msp, pts_mm, layer="WALL")

    def _add_openings_for_class(cls: int, *, layer: str, block_name: str) -> None:
        mask = (class_map == cls).astype(np.uint8) * 255
        if mask.max() == 0:
            return
        contours2, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area2 = float(_env_float("IMAGE_DXF_OPENING_MIN_AREA_PX", 200.0))
        for cc in contours2:
            if float(cv2.contourArea(cc)) < min_area2:
                continue
            x, y, bw, bh = cv2.boundingRect(cc)
            if bw <= 1 or bh <= 1:
                continue
            x_mm = float(x) * mm_per_px
            y_mm = (float(h) - float(y + bh)) * mm_per_px
            w_mm = float(bw) * mm_per_px
            h_mm = float(bh) * mm_per_px
            msp.add_blockref(
                block_name,
                (x_mm, y_mm),
                dxfattribs={"layer": layer, "xscale": w_mm, "yscale": h_mm},
            )

    _add_openings_for_class(2, layer="WINDOW", block_name="WINDOW")
    _add_openings_for_class(3, layer="DOOR", block_name="DOOR")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(out_path))
    return out_path


def image_to_dxf_ml(*, image_path: str | Path, dxf_path: str | Path) -> Path:
    _ensure_deps()
    import cv2

    from worker.segmentation import LocalSegmentationModel

    img_path = Path(image_path)
    out_path = Path(dxf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    color = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
    if color is None:
        raise ImageToDxfError(f"无法读取图片: {img_path}")

    h, w = int(color.shape[0]), int(color.shape[1])
    mm_per_px = _env_float("IMAGE_DXF_MM_PER_PX", 10.0)

    model = LocalSegmentationModel()
    class_map = model.predict(img_path)
    return _dxf_from_class_map(class_map=class_map, h=h, w=w, mm_per_px=mm_per_px, out_path=out_path)


def _find_static_root(p: Path) -> Path | None:
    cur = p.resolve()
    for parent in [cur] + list(cur.parents):
        if parent.name.lower() == "static":
            return parent
    return None


def _extract_session_id_from_dxf_path(p: Path) -> str | None:
    parts = [x.lower() for x in p.parts]
    for i, name in enumerate(parts):
        if name == "sessions" and i + 1 < len(parts):
            return p.parts[i + 1]
    return None


def _save_debug_images(*, image_path: Path, output_dxf_path: Path, enable_ai: bool) -> None:
    _ensure_deps()
    import cv2
    import numpy as np

    color = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if color is None:
        return
    gray = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)

    session_id = _extract_session_id_from_dxf_path(output_dxf_path) or uuid4().hex
    static_root = _find_static_root(output_dxf_path) or (Path(__file__).resolve().parents[1] / "static")
    debug_dir = static_root / "debug" / session_id
    debug_dir.mkdir(parents=True, exist_ok=True)

    cv2.imwrite(str(debug_dir / "debug_step1_gray.png"), gray)

    params = DetectParams(
        blur_kernel=_env_int("IMAGE_DXF_BLUR_KERNEL", 3),
        morph_close=_env_bool("IMAGE_DXF_MORPH_CLOSE", True),
        morph_kernel=_env_int("IMAGE_DXF_MORPH_KERNEL", 3),
        canny_low=_env_int("IMAGE_DXF_CANNY_LOW", 25),
        canny_high=_env_int("IMAGE_DXF_CANNY_HIGH", 75),
        hough_threshold=_env_int("IMAGE_DXF_HOUGH_THRESHOLD", 25),
        min_line=_env_int("IMAGE_DXF_MIN_LINE", 10),
        max_gap=_env_int("IMAGE_DXF_MAX_GAP", 25),
    )
    try:
        _, edges, _ = _run_canny_hough(gray, params=params)
    except Exception:
        edges = np.zeros_like(gray)
    cv2.imwrite(str(debug_dir / "debug_step3_opencv_edges.png"), edges)

    ai_mask_path = debug_dir / "debug_step2_ai_mask.png"
    cv2.imwrite(str(ai_mask_path), np.zeros_like(gray))


def _ai_wall_mask_is_usable(wall_mask) -> bool:
    import cv2
    import numpy as np

    if wall_mask is None or wall_mask.size == 0:
        return False
    if int(np.max(wall_mask)) == 0:
        return False
    h, w = int(wall_mask.shape[0]), int(wall_mask.shape[1])
    nz = int(np.count_nonzero(wall_mask))
    ratio = float(nz) / float(max(1, h * w))
    min_ratio = float(_env_float("IMAGE_DXF_AI_MIN_RATIO", 0.002))
    max_ratio = float(_env_float("IMAGE_DXF_AI_MAX_RATIO", 0.7))
    if ratio < min_ratio or ratio > max_ratio:
        return False
    contours, _ = cv2.findContours(wall_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False
    max_contours = int(_env_int("IMAGE_DXF_AI_MAX_CONTOURS", 250))
    min_large_area = float(_env_float("IMAGE_DXF_AI_MIN_LARGE_AREA_PX", 600.0))
    large = [c for c in contours if float(cv2.contourArea(c)) >= min_large_area]
    if not large:
        return False
    if len(contours) > max_contours and ratio < 0.2:
        return False
    return True


def convert_image_to_dxf(image_path: str | Path, output_dxf_path: str | Path) -> Path:
    try:
        use_ml = _env_bool("IMAGE_DXF_USE_LOCAL_SEG", True)
        img_path = Path(image_path)
        out_path = Path(output_dxf_path)
        _save_debug_images(image_path=img_path, output_dxf_path=out_path, enable_ai=use_ml)

        if use_ml:
            try:
                import cv2
                import numpy as np

                color = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
                if color is None:
                    raise ImageToDxfError(f"无法读取图片: {img_path}")
                h, w = int(color.shape[0]), int(color.shape[1])
                mm_per_px = _env_float("IMAGE_DXF_MM_PER_PX", 10.0)

                from worker.segmentation import LocalSegmentationModel

                model = LocalSegmentationModel()
                class_map = model.predict(img_path)
                wall_mask = (class_map == 1).astype(np.uint8) * 255
                try:
                    session_id = _extract_session_id_from_dxf_path(out_path) or uuid4().hex
                    static_root = _find_static_root(out_path) or (Path(__file__).resolve().parents[1] / "static")
                    debug_dir = static_root / "debug" / session_id
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    import cv2

                    cv2.imwrite(str(debug_dir / "debug_step2_ai_mask.png"), wall_mask)
                except Exception:
                    pass
                if not _ai_wall_mask_is_usable(wall_mask):
                    raise ImageClarityError("AI mask unusable, falling back to OpenCV")
                out = _dxf_from_class_map(class_map=class_map, h=h, w=w, mm_per_px=mm_per_px, out_path=out_path)
            except (ImportError, ModuleNotFoundError, RuntimeError, ImageClarityError):
                out = image_to_dxf(image_path=img_path, dxf_path=out_path)
        else:
            out = image_to_dxf(image_path=img_path, dxf_path=out_path)
    except ImageClarityError:
        raise
    except ImageToDxfError:
        raise
    except Exception as e:
        raise ImageToDxfError(str(e))

    try:
        import ezdxf

        doc = ezdxf.readfile(str(out))
        msp = doc.modelspace()
        wall_entities = [e for e in msp if str(getattr(e.dxf, "layer", "")).upper() == "WALL"]

        seg_count = 0
        for e in wall_entities:
            t = e.dxftype()
            if t == "LINE":
                seg_count += 1
            elif t == "LWPOLYLINE":
                pts = list(e.get_points("xy"))  # type: ignore[attr-defined]
                if len(pts) >= 2:
                    seg_count += len(pts) - 1
                    if bool(getattr(e, "closed", False)) and len(pts) >= 3:
                        seg_count += 1
            elif t == "POLYLINE":
                pts = list(e.vertices())  # type: ignore[attr-defined]
                if len(pts) >= 2:
                    seg_count += len(pts) - 1
                    if bool(getattr(e, "is_closed", False)) and len(pts) >= 3:
                        seg_count += 1

        if seg_count < 4:
            raise ImageClarityError("DXF 线条过少，疑似图片清晰度不足")
    except ImageClarityError:
        raise
    except Exception as e:
        raise ImageToDxfError(f"DXF 校验失败: {e}")
    return out

