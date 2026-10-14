# 生成和修改地图

本文供需要重建地图或修改布局的人使用。直接游玩请到 [Release 页面](https://github.com/hasbai/TF3_YRD/releases) 下载地图包，阅读包内 `使用说明.md`。

## 本地生成

在仓库根目录执行。需要 Python 3.11 及以上版本，以及中文字体。

```sh
python3 -m venv .venv
```

激活虚拟环境：

- macOS / Linux：`source .venv/bin/activate`
- Windows PowerShell：`.venv\Scripts\Activate.ps1`。创建环境时可用 `python` 替代 `python3`。

```sh
python -m pip install -r requirements.txt
python scripts/download_data.py
python scripts/build_map.py
python tests/check_geometry.py
python tests/check_package.py
python scripts/package.py
```

构建不需要安装游戏。脚本会创建输出目录，默认生成：

| 路径 | 内容 |
| --- | --- |
| `cache/` | 原始高程瓦片、地理数据、源文件 SHA256 及派生数组 |
| `build/YRD_1950/` | 高度图、生态蒙版、城市产业 Lua、预览与使用说明 |
| `build/TF3_YRD_v<版本>.zip` | 地图导入包 |
| `build/TF3_YRD_v<版本>.zip.sha256` | ZIP 校验值 |

预览图会自动查找 Windows 微软雅黑、macOS 黑体或宋体、Linux Noto Sans CJK 或文泉驿字体。未找到字体时，给构建命令加 `--font /path/to/font.ttf`。

三个生成脚本均支持 `--config`、`--cache`、`--output`。构建脚本另使用 `--font` 指定预览字体。修改路径时，各步骤应使用同一套路径；检查脚本也支持这些路径参数。

如需检查 Lua 语法，先安装 `lua` 并确保命令可用。`tests/check_package.py` 在未找到 `lua` 时会跳过语法检查，并输出提示。

## 配置与布局

| 文件 | 修改内容 |
| --- | --- |
| [config/map.json](../config/map.json) | 版本、中心、边长、旋转角、分辨率、高程、年份和随机种子 |
| [data/layout.json](../data/layout.json) | 城市人口等级、需求、产业类型与地理位置 |
| [data/navigation.json](../data/navigation.json) | 简化支流和游戏连接航道 |
| [data/sea-navigation.json](../data/sea-navigation.json) | 独立海域连通检查点，不用于雕刻航道 |

`rotation_deg` 表示地理内容顺时针旋转的角度。地形、水体、城市和产业共用这一变换。实际地图为旋转后的方形；经纬度包围盒只用于下载数据。

范围、DEM zoom 或源数据需求改变后，先运行下载脚本补齐缓存。每次修改地图配置或布局后，重新构建、检查并打包。改变加工链时，同步调整消费端需求。

## 缓存与重建

下载脚本只补缺失文件，中断后可重跑。改变地图范围时保留 `cache/`，复用已有高程和 Natural Earth 数据。

v0.3.0 使用 2862 张 zoom 12 高程瓦片。首次制作时复用 v0.2.0 的 1806 张，补下载 1056 张；三份 Natural Earth 文件全部复用。再次执行时，复用数量以本地缓存为准。

高程源文件的 SHA256 记录在 `cache/dem_manifest.json`。新范围必须从原始数据重新生成地形；旧派生数组不能作为新版原始高程。

相同配置、数据、依赖和字体可重建同一内容。跨平台字体差异可能改变预览图。

## 文档与发布

| 文档 | 用途 |
| --- | --- |
| [README](../README.md) | 玩家下载、导入概览与开局建议 |
| [导入指南模板](import-guide.md) | 构建时生成包内 `使用说明.md` |
| [来源与制作口径模板](methodology.md) | 构建时生成包内 `docs/来源与制作口径.md` |
| [AGENTS.md](../AGENTS.md) | 开发约束、完整验收与发布要求 |

两份模板中的 `{{…}}` 由构建脚本填入。玩家使用 ZIP 内已填好的文档。

只改 README 或本文，无需重新构建地图。修改导入指南或来源模板会影响包内文档，下次构建时才会写入输出目录。修改代码后运行 `ruff check scripts tests`；文档提交前运行 `git diff --check`。

地图修改后须检查实际地形与产业预览，并更新 `docs/preview.png`。离线检查覆盖文件格式、坐标、陆水位置、点位间距、静态供需链和水系连通。游戏导入、船舶寻路与经济可玩性需在游戏中单独验收。

新版本按 [仓库发布约定](../AGENTS.md#提交与发布) 提交、推送并发布 GitHub Release。原始缓存、构建目录和虚拟环境不提交 Git。
