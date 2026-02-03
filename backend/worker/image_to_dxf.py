import os
from dataclasses import dataclass
from pathlib import Path


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
    return edges, lines


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
        raise RuntimeError(f"无法读取图片: {img_path}")
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

    edges, lines = _run_canny_hough(gray, params=params)
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
        edges2, lines2 = _run_canny_hough(gray, params=aggressive)
        raw_count2 = 0 if lines2 is None else int(lines2.reshape(-1, 4).shape[0])
        if raw_count2 > raw_count:
            edges, lines, raw_count = edges2, lines2, raw_count2

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
        edges3, lines3 = _run_canny_hough(gray, params=strict)
        raw_count3 = 0 if lines3 is None else int(lines3.reshape(-1, 4).shape[0])
        if 0 < raw_count3 < raw_count:
            edges, lines, raw_count = edges3, lines3, raw_count3

    if raw_count == 0 and _env_bool("IMAGE_DXF_FALLBACK_CONTOUR", True):
        try:
            import numpy as np
            import cv2

            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            pad = _env_int("IMAGE_DXF_FALLBACK_PAD", 2)
            if contours:
                c = max(contours, key=cv2.contourArea)
                x, y, w, h2 = cv2.boundingRect(c)
                x0 = max(0, int(x) - pad)
                y0 = max(0, int(y) - pad)
                x1 = min(int(gray.shape[1]) - 1, int(x + w) + pad)
                y1 = min(int(gray.shape[0]) - 1, int(y + h2) + pad)
            else:
                x0, y0 = pad, pad
                x1 = max(pad + 4, int(gray.shape[1]) - 1 - pad)
                y1 = max(pad + 4, int(gray.shape[0]) - 1 - pad)
            if (x1 - x0) >= 4 and (y1 - y0) >= 4:
                lines = np.asarray(
                    [
                        [x0, y0, x1, y0],
                        [x1, y0, x1, y1],
                        [x1, y1, x0, y1],
                        [x0, y1, x0, y0],
                    ],
                    dtype=np.float64,
                )
                raw_count = int(lines.reshape(-1, 4).shape[0])
        except Exception:
            pass

    debug = _env_bool("IMAGE_DXF_DEBUG", False)
    if debug:
        debug_dir = os.getenv("IMAGE_DXF_DEBUG_DIR", "").strip()
        out_dir = Path(debug_dir) if debug_dir else img_path.parent
        _save_debug_images(out_dir=out_dir, gray=gray, edges=edges, color=color, lines=lines)

    h = full_h
    mm_per_px = _env_float("IMAGE_DXF_MM_PER_PX", 10.0)

    import ezdxf
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

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
        print(f"Merged {raw_count} lines into {merged_count} clean wall axes")

        for (x1, y1, x2, y2) in segs:
            x1o = float(x1) + float(off_x)
            y1o = float(y1) + float(off_y)
            x2o = float(x2) + float(off_x)
            y2o = float(y2) + float(off_y)
            sx = float(x1o) * mm_per_px
            sy = float(h - float(y1o)) * mm_per_px
            ex = float(x2o) * mm_per_px
            ey = float(h - float(y2o)) * mm_per_px
            msp.add_line((sx, sy), (ex, ey))
    else:
        print("[WARN] No lines detected. DXF will be empty.")
    doc.saveas(str(out_path))
    return out_path

