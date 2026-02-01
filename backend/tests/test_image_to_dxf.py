from pathlib import Path

import pytest


def test_image_to_dxf_creates_lines(tmp_path: Path):
    try:
        import cv2
        import numpy as np
    except Exception:
        pytest.skip("opencv/numpy not available")

    img = np.full((240, 320, 3), 255, np.uint8)
    cv2.rectangle(img, (40, 40), (280, 200), (0, 0, 0), 3)
    png_path = tmp_path / "room.png"
    cv2.imwrite(str(png_path), img)

    from worker.image_to_dxf import image_to_dxf

    dxf_path = tmp_path / "room.dxf"
    image_to_dxf(image_path=png_path, dxf_path=dxf_path)

    assert dxf_path.exists()
    assert dxf_path.stat().st_size > 1024

    try:
        import ezdxf
    except Exception:
        return
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    line_count = len(list(msp.query("LINE")))
    assert 1 <= line_count <= 64

