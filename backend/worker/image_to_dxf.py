import os
import subprocess
import sys
from pathlib import Path


def _ensure_deps():
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
        import ezdxf  # noqa: F401
        return
    except Exception:
        pass

    env = os.environ.copy()
    env.setdefault("NO_PROXY", "*")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "opencv-python-headless", "numpy", "ezdxf"],
        env=env,
    )

def _merge_lines_pairwise(lines, *, angle_tol_deg: float, dist_tol_px: float, gap_tol_px: float, min_len_px: float):
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


def image_to_dxf(*, image_path: str | Path, dxf_path: str | Path) -> Path:
    _ensure_deps()
    import cv2
    import ezdxf
    import numpy as np

    img_path = Path(image_path)
    out_path = Path(dxf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    gray = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise RuntimeError(f"无法读取图片: {img_path}")

    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)

    h, w = edges.shape[:2]
    mm_per_px = float(os.getenv("IMAGE_DXF_MM_PER_PX", "10.0"))

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180.0,
        threshold=int(os.getenv("IMAGE_DXF_HOUGH_THRESHOLD", "80")),
        minLineLength=int(os.getenv("IMAGE_DXF_MIN_LINE", "30")),
        maxLineGap=int(os.getenv("IMAGE_DXF_MAX_GAP", "10")),
    )

    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    if lines is not None:
        raw_count = int(lines.reshape(-1, 4).shape[0])
        angle_tol = float(os.getenv("IMAGE_DXF_MERGE_ANGLE_TOL", "5.0"))
        dist_tol = float(os.getenv("IMAGE_DXF_MERGE_DIST_TOL", "10.0"))
        gap_tol = float(os.getenv("IMAGE_DXF_MERGE_GAP_TOL", os.getenv("IMAGE_DXF_MAX_GAP", "10")))
        min_merged = float(os.getenv("IMAGE_DXF_MIN_MERGED_LINE_PX", os.getenv("IMAGE_DXF_MIN_LINE", "30")))
        do_merge = os.getenv("IMAGE_DXF_MERGE", "1").strip().lower() not in ("0", "false", "no")

        segs = _merge_lines_pairwise(
            lines,
            angle_tol_deg=angle_tol,
            dist_tol_px=dist_tol,
            gap_tol_px=gap_tol,
            min_len_px=min_merged,
        ) if do_merge else lines.reshape(-1, 4).astype("float64")

        ortho_tol = float(os.getenv("IMAGE_DXF_ORTHO_TOL", "5.0"))
        do_ortho = os.getenv("IMAGE_DXF_ORTHO", "1").strip().lower() not in ("0", "false", "no")
        if do_ortho and segs.size:
            segs = _orthogonalize_lines(segs, tol_deg=ortho_tol)

        merged_count = int(segs.shape[0])
        print(f"Merged {raw_count} lines into {merged_count} clean wall axes")

        for (x1, y1, x2, y2) in segs:
            sx = float(x1) * mm_per_px
            sy = float(h - float(y1)) * mm_per_px
            ex = float(x2) * mm_per_px
            ey = float(h - float(y2)) * mm_per_px
            msp.add_line((sx, sy), (ex, ey))

    doc.saveas(str(out_path))
    return out_path

