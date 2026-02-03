export type CameraViewKey =
  | "main"
  | "top"
  | "wall"
  | "elev_n"
  | "elev_s"
  | "elev_e"
  | "elev_w"
  | "corner_ne"
  | "corner_nw"
  | "corner_se"
  | "corner_sw"

export const CAMERA_VIEW_LABEL: Record<CameraViewKey, string> = {
  main: "主视角",
  top: "顶视图",
  wall: "墙面视角",
  elev_n: "立面N",
  elev_s: "立面S",
  elev_e: "立面E",
  elev_w: "立面W",
  corner_ne: "东北角",
  corner_nw: "西北角",
  corner_se: "东南角",
  corner_sw: "西南角",
}

export const CAMERA_VIEW_DEFAULTS: CameraViewKey[] = [
  "main",
  "top",
  "elev_n",
  "elev_s",
  "elev_e",
  "elev_w",
  "corner_ne",
  "corner_nw",
  "corner_se",
  "corner_sw",
]
