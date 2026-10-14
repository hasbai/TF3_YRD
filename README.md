# TF3_YRD

《狂热运输 3》长三角 1950 地图生成代码。地图素材包从 [GitHub Releases](https://github.com/hasbai/TF3_YRD/releases) 下载，在原生地图编辑器导入。

当前范围约 350 × 350 km，覆盖南京—上海—杭州—宁波及附近城市。输出最大实验档 Gigantomaniac 方图，游戏尺寸 28.672 × 28.672 km，7169² 的 16 位高度图。16 座城市从预计约 19—64 人起步；32 个产业点组成农业、林业、建材、纺织、煤铁、机械及水运链。

![地图离线预览](docs/preview.png)

## 制作过程

1. 从 Mapzen Terrain Tiles 下载 zoom 12 真实高程，拼接并投影到同一局部坐标系。
2. 将约 350 km 现实区域水平压缩约 12.21 倍，高地按约 10% 缩放，为交通建设保留空间。
3. 按 Natural Earth 海岸、天然湖泊和长江数据雕刻水面，补绘简化支流、运河和连接航道。
4. 按高地、平原、水岸和建设预留区生成植被蒙版，平整城市和产业位置。
5. 输出 PNG 和原生 `towns_industries` Lua，检查陆水位置、点位间距、货物链及航道连通，再打包 ZIP。

没有运行 Windows 版 TPF3 Map Studio。参考了它的公开源码和作者游戏测试记录，核对人口规模因子、产业资源路径和温带生态蒙版格式。来源固定到具体提交，见 [制作方法与来源](docs/methodology.md)。

地图是 **1950 年小城开局的现代地理改编**。植被为设计分布，支流为简化补绘；不是 1950 年测绘复原。游戏内树木、产业建筑、船舶寻路和经济尚未验收。

## 生成地图

Python 3.11 及以上。预览图需要中文字体：Windows 自动查找微软雅黑，macOS 查找黑体，Linux 查找 Noto Sans CJK；也可通过 `--font` 指定字体文件。

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/download_data.py
python scripts/build_map.py
python tests/check_package.py
python scripts/package.py
```

下载会缓存 1806 张高程瓦片，首次运行需要联网。下载中断后可重跑，已有文件不会重复下载。原始数据放在 `cache/`，地图输出到 `build/YRD_1950/`，版本 ZIP 和校验值位于 `build/`。

三个脚本均支持 `--config`、`--cache`、`--output`；构建还支持 `--font`。从空的输出目录执行会自动创建全部文件，不依赖本机游戏或上一次构建。`tests/check_package.py` 额外检查实际 PNG 样本和 Lua；Lua 语法校验在安装了 `lua` 的环境执行。

相同配置、数据、依赖和字体可重建同一内容；跨平台字体不同可能使预览图不同。下载清单保存源文件 SHA256，Release 也附地图包 SHA256。

## 调整地图

- [config/map.json](config/map.json)：中心、边长、分辨率、高程缩放、年份和固定随机种子。
- [data/layout.json](data/layout.json)：城市人口等级与需求、产业类型和原始地理位置。
- [data/navigation.json](data/navigation.json)：简化支流和游戏连通航道。
- [scripts/](scripts/)：下载、构建和打包。
- [docs/import-guide.md](docs/import-guide.md)：Windows 导入步骤；参数占位符由构建自动填入。

改变中心、范围或布局后，先重跑下载，再生成、检查和打包。加工链的消费端必须同步调整。

## 数据与许可

自有生成代码为 MIT。高程与地理数据分别遵循原数据许可和署名要求，不由代码许可替代。

Mapzen Terrain Tiles；Global GMTED2010 and SRTM terrain data courtesy of the U.S. Geological Survey；Global ETOPO1 terrain data courtesy of the U.S. National Oceanic and Atmospheric Administration。海岸、主要湖泊和长江数据：Made with Natural Earth（公共领域）。详细来源、修改方式和人口口径见 [docs/methodology.md](docs/methodology.md)。

原始缓存和地图 ZIP 不放入 Git；地图文件通过 Release 分发。
