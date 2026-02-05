from __future__ import annotations

from pathlib import Path

import ezdxf

from app.modules.engineering.services import modify_cad_structure
from app.modules.engineering.schemas import CADActionType, CADModificationCommand


def test_move_wall_right_500mm(tmp_path: Path, monkeypatch):
    doc = ezdxf.new(setup=True)
    if not doc.layers.has_entry("WALL"):
        doc.layers.new(name="WALL")
    msp = doc.modelspace()
    msp.add_line((0, 0), (1000, 0), dxfattribs={"layer": "WALL"})
    src_path = tmp_path / "input.dxf"
    doc.saveas(str(src_path))

    import app.modules.engineering.services as eng_services

    monkeypatch.setenv("LLM_PROVIDER", "none")
    monkeypatch.setattr(
        eng_services,
        "parse_cad_modification_command",
        lambda _: CADModificationCommand(action_type=CADActionType.MOVE_WALL, target_description="墙", value=500.0),
    )

    svg_preview, out_path = modify_cad_structure(str(src_path), "把客厅的墙向右移动 500mm")
    assert isinstance(svg_preview, str) and svg_preview.strip()
    assert "<svg" in svg_preview
    assert Path(out_path).exists()

    doc2 = ezdxf.readfile(out_path)
    line = next(e for e in doc2.modelspace() if e.dxftype() == "LINE")
    assert float(line.dxf.start.x) == 500.0
    assert float(line.dxf.end.x) == 1500.0
