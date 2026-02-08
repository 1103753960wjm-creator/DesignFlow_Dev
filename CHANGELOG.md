# Changelog

## 2026-02-08

### Added

- 本地语义分割推理模块与 Image→DXF 的分割矢量化流程（负责人：Trae）
- 图片转 DXF 本地推理验证脚本（负责人：Trae）
- Image→DXF 混合策略调试图片输出与接口字段 `debug_images`（负责人：Trae）

### Changed

- DXF 输出默认设置单位为毫米（`$INSUNITS=4`）（负责人：Trae）
- 图片转 DXF 流程默认优先走本地分割，失败自动回退旧算法（负责人：Trae）

### Fixed

- 旧算法 contour 回退分支不产出 `LINE` 导致单测失败的问题（负责人：Trae）
- 测试用例避免触发 PyTorch 预训练权重下载导致卡死（负责人：Trae）

