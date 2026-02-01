import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from uuid import uuid4


def _ensure_ezdxf():
    try:
        import ezdxf
        return
    except Exception:
        pass

    import subprocess

    try:
        os.environ.setdefault("NO_PROXY", "*")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ezdxf"])
        return
    except Exception:
        pass

    try:
        import ensurepip

        ensurepip.bootstrap()
        os.environ.setdefault("NO_PROXY", "*")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ezdxf"])
    except Exception as e:
        raise SystemExit(f"Failed to install ezdxf into Blender Python: {e}")


def _parse_args() -> tuple[str, str, float]:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    input_path = None
    output_dir = None
    scale = None

    it = iter(argv)
    for token in it:
        if token in ("--input", "-i"):
            input_path = next(it, None)
        elif token in ("--output", "-o"):
            output_dir = next(it, None)
        elif token == "--scale":
            raw = next(it, None)
            scale = float(raw) if raw is not None else None

    if not input_path or not output_dir:
        raise SystemExit("Usage: --input <dxf_path> --output <output_dir> [--scale <float>]")

    if scale is None:
        scale = float(os.getenv("DXF_SCALE", "0.001"))

    return input_path, output_dir, float(scale)


@dataclass(frozen=True)
class Bounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def cx(self) -> float:
        return (self.min_x + self.max_x) / 2.0

    @property
    def cy(self) -> float:
        return (self.min_y + self.max_y) / 2.0

    @property
    def width(self) -> float:
        return max(0.001, self.max_x - self.min_x)

    @property
    def height(self) -> float:
        return max(0.001, self.max_y - self.min_y)


def _iter_lines(msp) -> Iterable[tuple[tuple[float, float], tuple[float, float]]]:
    for e in msp.query("LINE"):
        s = e.dxf.start
        t = e.dxf.end
        yield (float(s.x), float(s.y)), (float(t.x), float(t.y))


def _bounds_from_lines(lines: list[tuple[tuple[float, float], tuple[float, float]]]) -> Bounds:
    xs: list[float] = []
    ys: list[float] = []
    for (x1, y1), (x2, y2) in lines:
        xs.extend([x1, x2])
        ys.extend([y1, y2])
    if not xs or not ys:
        return Bounds(-1.0, -1.0, 1.0, 1.0)
    return Bounds(min(xs), min(ys), max(xs), max(ys))


def _clear_scene(bpy):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False, confirm=False)
    for datablock in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.lights,
        bpy.data.cameras,
        bpy.data.curves,
    ):
        for item in list(datablock):
            try:
                datablock.remove(item)
            except Exception:
                pass


def _create_wall(bpy, *, p1: tuple[float, float], p2: tuple[float, float], thickness: float, height: float):
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return None

    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    angle = math.atan2(dy, dx)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, height / 2.0))
    obj = bpy.context.active_object
    obj.scale = (length / 2.0, thickness / 2.0, height / 2.0)
    obj.rotation_euler = (0.0, 0.0, angle)
    obj.name = f"Wall_{uuid4().hex[:8]}"
    return obj


def _create_floor(bpy, bounds: Bounds, z: float = 0.0):
    cx, cy = bounds.cx, bounds.cy
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(cx, cy, z))
    obj = bpy.context.active_object
    obj.scale = (bounds.width / 2.0, bounds.height / 2.0, 1.0)
    obj.name = "Floor"
    return obj


def _try_boolean_union(bpy, objects):
    if not objects:
        return None
    base = objects[0]
    bpy.ops.object.select_all(action="DESELECT")
    base.select_set(True)
    bpy.context.view_layer.objects.active = base

    for other in objects[1:]:
        try:
            mod = base.modifiers.new(name=f"Union_{uuid4().hex[:6]}", type="BOOLEAN")
            mod.operation = "UNION"
            mod.object = other
            try:
                mod.solver = "FAST"
            except Exception:
                pass
            bpy.ops.object.modifier_apply(modifier=mod.name)

            bpy.ops.object.select_all(action="DESELECT")
            other.select_set(True)
            bpy.context.view_layer.objects.active = other
            bpy.ops.object.delete(use_global=False, confirm=False)

            bpy.ops.object.select_all(action="DESELECT")
            base.select_set(True)
            bpy.context.view_layer.objects.active = base
        except Exception:
            continue
    return base


def _look_at(obj, target: tuple[float, float, float]):
    import mathutils

    direction = mathutils.Vector(target) - obj.location
    rot_quat = direction.to_track_quat("-Z", "Y")
    obj.rotation_euler = rot_quat.to_euler()


def _create_camera(bpy, *, name: str, location: tuple[float, float, float], look_at: tuple[float, float, float], ortho: bool):
    cam_data = bpy.data.cameras.new(name=name)
    cam_obj = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    cam_obj.location = location
    _look_at(cam_obj, look_at)
    if ortho:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = 12.0
    else:
        cam_data.type = "PERSP"
        cam_data.lens = 28
    return cam_obj


def _enable_depth_compositor(bpy):
    scene = bpy.context.scene
    for vl in scene.view_layers:
        try:
            vl.use_pass_z = True
        except Exception:
            pass

    if hasattr(scene, "compositing_node_group"):
        tree = bpy.data.node_groups.new(name=f"DepthComp_{uuid4().hex[:8]}", type="CompositorNodeTree")
        scene.compositing_node_group = tree

        try:
            tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        except Exception:
            pass

        rl = tree.nodes.new(type="CompositorNodeRLayers")
        norm = tree.nodes.new(type="CompositorNodeNormalize")
        out = tree.nodes.new(type="NodeGroupOutput")
        rl.location = (-300, 0)
        norm.location = (-80, 0)
        out.location = (160, 0)

        depth_out = rl.outputs.get("Depth") or rl.outputs[0]
        image_in = out.inputs.get("Image") or out.inputs[0]
        tree.links.new(depth_out, norm.inputs[0])
        tree.links.new(norm.outputs[0], image_in)
    else:
        scene.use_nodes = True
        tree = scene.node_tree
        for n in list(tree.nodes):
            tree.nodes.remove(n)

        rl = tree.nodes.new(type="CompositorNodeRLayers")
        norm = tree.nodes.new(type="CompositorNodeNormalize")
        comp = tree.nodes.new(type="CompositorNodeComposite")
        rl.location = (-300, 0)
        norm.location = (-80, 0)
        comp.location = (160, 0)

        tree.links.new(rl.outputs["Depth"], norm.inputs[0])
        tree.links.new(norm.outputs[0], comp.inputs[0])

    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "BW"
    scene.render.image_settings.color_depth = "8"


def _render_depth(bpy, *, camera_obj, out_path: Path, resolution: tuple[int, int] = (1280, 720)):
    scene = bpy.context.scene
    scene.camera = camera_obj
    scene.render.resolution_x = int(resolution[0])
    scene.render.resolution_y = int(resolution[1])
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)


def _export_obj(bpy, out_path: Path):
    bpy.ops.object.select_all(action="SELECT")
    if hasattr(bpy.ops, "export_scene") and hasattr(bpy.ops.export_scene, "obj"):
        try:
            bpy.ops.export_scene.obj(
                filepath=str(out_path),
                use_selection=False,
                use_materials=False,
                axis_forward="-Z",
                axis_up="Y",
            )
            return
        except Exception:
            pass

    if hasattr(bpy.ops, "wm") and hasattr(bpy.ops.wm, "obj_export"):
        try:
            bpy.ops.wm.obj_export(
                filepath=str(out_path),
                forward_axis="NEGATIVE_Z",
                up_axis="Y",
            )
            return
        except Exception:
            pass

    raise RuntimeError("OBJ export operator is not available")


def main():
    input_path, output_dir, scale = _parse_args()

    _ensure_ezdxf()

    import bpy
    import ezdxf

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    _clear_scene(bpy)

    doc = ezdxf.readfile(str(input_path))
    msp = doc.modelspace()
    raw_lines = list(_iter_lines(msp))
    lines = [((x1 * scale, y1 * scale), (x2 * scale, y2 * scale)) for (x1, y1), (x2, y2) in raw_lines]

    bounds = _bounds_from_lines(lines)

    wall_height = 2.8
    wall_thickness = 0.2
    walls = []

    for p1, p2 in lines:
        wall = _create_wall(bpy, p1=p1, p2=p2, thickness=wall_thickness, height=wall_height)
        if wall is not None:
            walls.append(wall)

    if os.getenv("WALL_BOOLEAN_UNION", "").strip().lower() in ("1", "true", "yes"):
        before = len(walls)
        merged = _try_boolean_union(bpy, walls)
        after = 1 if merged is not None else before
        print(f"Wall boolean union: {before} -> {after}")

    _create_floor(bpy, bounds)

    center = (bounds.cx, bounds.cy, 1.4)
    top_cam = _create_camera(
        bpy,
        name="Top_View",
        location=(bounds.cx, bounds.cy, 10.0),
        look_at=(bounds.cx, bounds.cy, 0.0),
        ortho=True,
    )

    margin = 1.2
    main_cam = _create_camera(
        bpy,
        name="Main_View",
        location=(bounds.min_x + margin, bounds.min_y + margin, 1.6),
        look_at=center,
        ortho=False,
    )

    longest = None
    for p1, p2 in lines:
        length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if longest is None or length > longest[0]:
            longest = (length, p1, p2)

    if longest is not None:
        _, p1, p2 = longest
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length
        mx, my = (p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0
        wall_cam = _create_camera(
            bpy,
            name="Wall_View",
            location=(mx + nx * 3.0, my + ny * 3.0, 1.6),
            look_at=(bounds.cx, bounds.cy, 1.2),
            ortho=False,
        )
    else:
        wall_cam = _create_camera(
            bpy,
            name="Wall_View",
            location=(bounds.max_x - 1.0, bounds.min_y + 1.0, 1.6),
            look_at=center,
            ortho=False,
        )

    _enable_depth_compositor(bpy)

    _render_depth(bpy, camera_obj=top_cam, out_path=out_dir / "depth_top.png")
    _render_depth(bpy, camera_obj=main_cam, out_path=out_dir / "depth_main.png")
    _render_depth(bpy, camera_obj=wall_cam, out_path=out_dir / "depth_wall.png")

    try:
        import shutil

        src = out_dir / "depth_main.png"
        dst = out_dir / "depth_0.png"
        if src.exists():
            shutil.copyfile(src, dst)
    except Exception:
        pass

    _export_obj(bpy, out_path=out_dir / "model.obj")


if __name__ == "__main__":
    main()

