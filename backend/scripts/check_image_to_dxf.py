from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import ezdxf
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worker.image_to_dxf import convert_image_to_dxf


def main() -> None:
    img = Path(__file__).resolve().parents[1] / "assets" / "mock" / "test_room.png"
    mat = cv2.imread(str(img), cv2.IMREAD_GRAYSCALE)
    if mat is None:
        raise RuntimeError("read image failed")
    print(f"img_shape={mat.shape} min={int(mat.min())} max={int(mat.max())} mean={float(mat.mean()):.3f}", flush=True)
    out_dir = Path(tempfile.mkdtemp())
    out = out_dir / "out.dxf"
    convert_image_to_dxf(img, out)
    doc = ezdxf.readfile(str(out))
    walls = [e for e in doc.modelspace() if str(getattr(e.dxf, "layer", "")).upper() == "WALL"]
    seg_count = 0
    for e in walls:
        t = e.dxftype()
        if t == "LINE":
            seg_count += 1
        elif t == "LWPOLYLINE":
            pts = list(e.get_points("xy"))  # type: ignore[attr-defined]
            if len(pts) >= 2:
                seg_count += len(pts) - 1
                if bool(getattr(e, "closed", False)) and len(pts) >= 3:
                    seg_count += 1
    print(f"dxf={out}")
    print(f"wall_entities={len(walls)}")
    print(f"wall_segments={seg_count}")


if __name__ == "__main__":
    main()
