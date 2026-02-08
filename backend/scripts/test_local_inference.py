import os
import sys
import tempfile
from pathlib import Path


def main() -> int:
    os.environ.setdefault("IMAGE_DXF_USE_LOCAL_SEG", "1")

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    image_path = Path(__file__).resolve().parents[1] / "assets" / "mock" / "test_room.png"
    if not image_path.exists():
        raise FileNotFoundError(f"Missing input image: {image_path}")

    with tempfile.TemporaryDirectory(prefix="local_infer_") as td:
        out_path = Path(td) / "out.dxf"

        from worker.image_to_dxf import convert_image_to_dxf

        convert_image_to_dxf(image_path=image_path, output_dxf_path=out_path)

        if not out_path.exists():
            raise RuntimeError("DXF was not generated")

        try:
            import ezdxf
        except Exception:
            print(f"DXF generated at: {out_path}")
            return 0

        doc = ezdxf.readfile(str(out_path))
        msp = doc.modelspace()
        entities_count = len(list(msp))
        print(f"DXF generated at: {out_path}")
        print(f"Entities Count: {entities_count}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

