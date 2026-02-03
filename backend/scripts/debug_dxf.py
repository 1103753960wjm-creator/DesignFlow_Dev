import os
import sys
import argparse
from pathlib import Path


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="assets/mock/test_room.png")
    parser.add_argument("--out", default="")
    parser.add_argument("--debug-dir", default="")
    args = parser.parse_args()

    os.environ.setdefault("IMAGE_DXF_DEBUG", "true")
    if args.debug_dir:
        os.environ["IMAGE_DXF_DEBUG_DIR"] = args.debug_dir

    from worker.image_to_dxf import image_to_dxf

    img = Path(args.image)
    if not img.exists():
        raise SystemExit(f"图片不存在: {img}")

    out = Path(args.out) if args.out else img.with_suffix(".dxf")
    image_to_dxf(image_path=img, dxf_path=out)
    print(out.resolve())


if __name__ == "__main__":
    main()

