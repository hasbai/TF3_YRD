# TF3_YRD 工作约定

## 最高优先级

1. NO FLUFF：删除套话、重复和无用解释。
2. NO OVERENGINEERING：采用最简单的可用方案，不增加无关功能、抽象或依赖。
3. NO DEFENSIVE DISCLAIMER：避免过量警告、免责声明和猜测性风险说明。
4. 用户当前指令优先于本文件；保留用户无关改动。

## 多代理

主代理在制定大型方案前、同一错误重复出现时，以及宣布长任务完成前，必须调用 `architect`。等待审查结果并处理发现的问题后再继续。

## 项目与入口

本项目生成《狂热运输 3》长三角 1950 小城开局地图的原生编辑器导入包。

- `config/map.json`：版本、中心、旋转角、现实/游戏边长、网格、高程和种子。
- `data/layout.json`：城市规模、需求、产业与地理位置。
- `data/navigation.json`：简化支流与游戏连通航道。
- `data/sea-navigation.json`：独立海域连通检查点，不用于雕刻航道。
- `scripts/common.py`：路径、配置、地理与地图坐标正反变换。
- `scripts/download_data.py`、`build_map.py`、`package.py`：缓存下载、构建、打包。
- `docs/import-guide.md`、`methodology.md`：导入步骤和数据口径模板。
- `build/YRD_1950/`：生成的导入文件；`build/TF3_YRD_v*.zip`：发布包。

## 数据复用

- 优先使用 `cache/` 中的原始 DEM 瓦片和 Natural Earth 文件，禁止为改范围而删除或重下载整份缓存。
- 范围或 DEM zoom 改变时，通过下载脚本计算所需瓦片，仅补缺失文件；保持原文件与 SHA256。
- 高程、海岸和地理资料不得用 AI 生成图片代替。提升数据精度前先确认现有来源和缓存可用性。
- 配置改变后重新生成派生高度图、水域与布局；旧派生数组不能当作新版原始高程。
- `cache/`、`build/` 和虚拟环境不提交 Git，源码、配置、布局和文档提交 Git。

## 地图约束

- 地形、水体、城市、产业、CSV 与 Lua 使用同一坐标变换。`rotation_deg` 为地理内容顺时针旋转角，北箭头同步旋转。
- 实际地图是旋转方形；经纬度 bbox 只是下载包围盒。清单同时记录旋转角和四角，图内判断使用地图坐标。
- 调整范围时保留用户指定城市和海岛，以及城市、产业的建设边距。海域要连续，不能靠穿陆开槽或内河绕行掩盖断海。
- 人口、植被、产业的设计估计明确标注，不冒充 1950 年实测复原。保留数据来源、许可和口径。
- 默认保持原生温带导入格式、1950 开局、统一水位和静态产业供需链；用户要求改变时同步更新配置与文档。

## 验证与预览

地图或生成逻辑变更后执行：

```sh
# 仅当范围、zoom 或源数据需求改变时运行；已有数据会复用。
python3 scripts/download_data.py
python3 scripts/build_map.py
python3 tests/check_geometry.py
python3 tests/check_package.py
python3 scripts/package.py
```

- 代码改动通过 `ruff check scripts tests` 和 `git diff --check`；依赖遵循 `requirements.txt`。
- 验证最终 PNG 编码、陆水位置、点位边距、Lua 语法、产业供需与水系连通。
- 海域连通必须检查最终 PNG 解码水面，并在独立海域蒙版中保留至少 16 游戏米岸边余量。
- 查看实际地形与产业两张预览；用户提供参考图时逐项对照范围、朝向、海岛与水面关系。更新 `docs/preview.png`。
- 离线通过不代表游戏验收通过。只有实际运行游戏后，才能声称已验证导入、船舶寻路或经济可玩性。
- 只改 AGENTS.md 或 README 等不影响导入包的文件时，无需重新下载或构建地图。

## 提交与发布

- 新版地图交付包含 GitHub Release；用户明确只要本地文件时按其要求。不能把本地 ZIP、未推送提交或 Release 草稿称为已发布。
- 发布前更新 `config/map.json` 版本，核对 README、预览、导入说明、来源口径和实际生成内容一致。
- 仅暂存本任务文件，提交并推送至 `origin`。发布标签 `v<version>` 必须指向包含本版配置、代码、布局和文档的提交。
- 在 `hasbai/TF3_YRD` 发布正式 Release，上传对应 ZIP 与 `.zip.sha256`。保留旧版本，避免覆盖已有标签或资产。
- Release 说明写清范围、旋转、城市/产业数量、导入参数、数据复用、已通过检查与尚未运行的游戏验收。
- 发布后读取远端提交、标签与 Release，核对资产名称、大小和 SHA256。最终回复提供真实 Release 链接。
