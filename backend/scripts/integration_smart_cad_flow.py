from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace

import ezdxf
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.modules.engineering.router import router as engineering_router
from app.modules.engineering.schemas import CADActionType, CADModificationCommand


def main() -> None:
    app = FastAPI()
    app.include_router(engineering_router, prefix="/api/v1/engineering")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="test-user")
    client = TestClient(app)

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        doc = ezdxf.new(setup=True)
        if not doc.layers.has_entry("WALL"):
            doc.layers.new(name="WALL")
        msp = doc.modelspace()
        msp.add_line((0, 0), (1000, 0), dxfattribs={"layer": "WALL"})
        msp.add_line((1000, 0), (1000, 800), dxfattribs={"layer": "WALL"})
        msp.add_line((1000, 800), (0, 800), dxfattribs={"layer": "WALL"})
        msp.add_line((0, 800), (0, 0), dxfattribs={"layer": "WALL"})
        src = tmp / "test.dxf"
        doc.saveas(str(src))

        with open(src, "rb") as f:
            resp = client.post("/api/v1/engineering/upload", files={"file": ("test.dxf", f, "application/dxf")})
        upload = resp.json()
        dxf_path = upload["dxf_file_path"]
        svg_before = upload["svg_preview"]

        import app.modules.engineering.services as eng_services

        eng_services.parse_cad_modification_command = lambda _: CADModificationCommand(
            action_type=CADActionType.DELETE_ITEM,
            target_description="north wall",
        )

        resp2 = client.post(
            "/api/v1/engineering/modify",
            json={"dxf_file_path": dxf_path, "user_prompt": "Remove the north wall"},
        )
        modify = resp2.json()
        svg_after = modify["svg_preview"]

        print(
            {
                "upload_status": resp.status_code,
                "modify_status": resp2.status_code,
                "dxf_file_path": dxf_path,
                "svg_before_len": len(svg_before),
                "svg_after_len": len(svg_after),
                "svg_before_lines": svg_before.count("<line"),
                "svg_after_lines": svg_after.count("<line"),
            }
        )


if __name__ == "__main__":
    main()
