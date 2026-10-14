# 来源与制作口径

制作日期：2026-10-14。

## 导入格式

- [Transport Fever 3 官方地图尺寸](https://wiki.transportfever3.com/doku.php?id=gamemanual:mapsizes)：Gigantomaniac 方图 28.672 km，7169 px；通过 `experimentalMapFeatures` 开启。
- [官方地图编辑器](https://wiki.transportfever3.com/doku.php?id=gamemanual:gamemodes:mapeditor)：16 位 PNG、生态蒙版与城市产业 Lua 导入，以及保存地图流程。
- [官方产业与货物](https://wiki.transportfever3.com/doku.php?id=gamemanual:simulation:industriescargos)：温带产业类型、初始需求和原料链。
- [TPF3 Map Studio](https://github.com/sharpi13822/TPF3-Map-Studio)，读取源码提交 `8126e8c1a63a50f42980ebc908e97592bae2aac2`：
  - `src/heightmap/towns_export.py`：作者记录人口由中间规模因子控制，0.2 约 19 人、1 约 98 人；前后因子保留 1。
  - `src/heightmap/industries_export.py`：作者实测原版温带产业资源路径 `::/industries/<tag>/<tag>.con`。
  - `src/heightmap/biome_mask.py`、`docs/SPIELWISSEN.en.md`、`src/gui/heightmap_guide.py`：温带蒙版灰度区间、Biome 1 的树群及实际导入步骤。

本包借鉴已记录的格式和测试结论，独立制作地理、地形和布局；没有运行 Studio 的 Windows 图形软件，也没有把作者实测冒称为本包在游戏中的验收。

v0.3.1 另核对本机游戏的 `base/content/gui.zip` 中 `gui/map_editor/map_editor.tl` 与 API 类型声明：高度图导入按钮会调用地形替换命令并记录 `Replacing terrain`；生态应用读取现有高度图。产业导入只复制位置、旋转、是否水上、资源路径和标签，不读取名称。包内的一次性名称命令使用 `Industry.construction`、`Construction.transf:getTransl()` 与 `api.cmd.makeEntitySetNameCmd`，按最终位置和资源路径匹配后改名。API 存在和 Lua 模拟检查不等于游戏内命令验收。

## 高程

[Mapzen Terrain Tiles / AWS Open Data](https://registry.opendata.aws/terrain-tiles/)。实际下载 {{TILE_COUNT}} 张 zoom {{ZOOM}} Terrarium 瓦片，来自 `elevation-tiles-prod`，全部下载完成。RGB 解码公式为 `R×256 + G + B/256 − 32768`。

世界坐标中心：{{CENTER}}。地理内容顺时针旋转 {{ROTATION}}°，南京—舟山接近图中左上—右下对角线。实际四角（依次为图中左下、右下、右上、左上）：{{CORNERS}}。下载包围盒：{{BBOX}}，包围盒角部不属于实际地图。采用中心纬度的局部等距近似，水平压缩约 {{SCALE}} 倍；DEM 逐像素逆变换到经纬度采样，海岸、城市、产业和航道使用相同变换。

源瓦片在本区地面分辨率约 {{SOURCE_SPACING}} m/px。本版直接使用 7169 px 制作网格；实际地图约 {{REAL_SIDE_KM}} km，对应实地网格约 {{REAL_GRID_SPACING}} m。输出为游戏 4 m 采样网格，其密度不代表实地 4 m 测绘精度。

改动：轻微平滑；将陆地起伏缩至约 10%；保证低地高于统一水位；单独雕刻海底、河床、湖盆；平整城市与产业位置。PNG 的黑白编码范围为 −20—240 m，实际地形约 −12—{{MAX_TERRAIN}} m。

地形数据署名：Mapzen Terrain Tiles。Global GMTED2010 and SRTM terrain data courtesy of the U.S. Geological Survey；Global ETOPO1 terrain data courtesy of the U.S. National Oceanic and Atmospheric Administration。瓦片为多源融合，未逐像元鉴定底层来源。[Mapzen 数据署名说明](https://github.com/tilezen/joerd/blob/master/docs/attribution.md)。

## 海岸、湖泊、河流

[Natural Earth 10m Physical Vectors](https://www.naturalearthdata.com/downloads/10m-physical-vectors/)，固定源提交 `ca96624a56bd078437bca8184e78163e5039ad19`，使用 `ne_10m_land`、`ne_10m_lakes`、`ne_10m_rivers_lake_centerlines`。其中“10m”表示 **1:1000 万制图比例尺**，不是 10 米精度。其数据为公共领域。[使用条款](https://www.naturalearthdata.com/about/terms-of-use/)。

天然湖泊保留；现代水库湖面排除。主要湖形与长江中心线来自上述地理数据，岸线和河道为现代概化数据。其余水系为地理定位的简化补绘。OpenStreetMap 查询未取得可用数据，成品不使用也不声称使用了 OSM 河岸或森林资料。

植被不是遥感分类结果，而是按高程、低地、固定种子随机斑块及建设预留区制作的设计分布。用于重现“山林—平原—水岸”的总体关系。

温带生态灰度 26、77、128 分别对应 Biome 0 的开阔草地、Biome 1 的草地树群、Biome 2 的深色草地。岸边使用深色草地作视觉过渡，不表示原生湿地分类。所报树群群落比例是蒙版区域比例，不是游戏实际树冠覆盖率。

## 人口

- 上海 1953 市区 6,204,417 人、南京 1,091,575 人、杭州 696,608 人：参考[1964 年普查资料中的 1953 比较列](https://zh.wikipedia.org/wiki/中华人民共和国第二次全国人口普查)。此处为二手整理，仅用于设计等级，1953 不能写成 1950 实数。
- 苏州 1949 市区 502,057 人：参考[苏州市地方志“苏州历史上的人口”](https://dfzb.suzhou.gov.cn/dfzb/szdq/201507/8d3b864be8d247b991dd1524605f7e9b.shtml)。边界与其他城市的普查整理列不完全可比，未据此推算精确城市间人口比例。
- 南京官方年鉴另有[1950 年非农业人口 101.05 万人](https://tjj.nanjing.gov.cn/material/njnj_2008/renkou/2-5.htm)，作为规模量级交叉参考；没有混作同口径市区人口。
- 其余城市人口为明确标注的游戏设计估计，CSV 中历史实数留空。

所有游戏规模压缩到中间因子 0.20—0.65，预计约 19—64 人；不使用现代地级市全域人口，也不是同比例人口模拟。

## 产业

农业、通海棉作、苏南纺织、宣城浙北林业、域外煤炭输入、马鞍山铁矿、上海制造、太湖与宁波、舟山沿海渔业按区域特色配置。点位可为避水、避免建筑冲突小幅调整；原始定位和调整后位置同时留在 CSV。

不能将这些点解释为 1950 年逐个真实企业的坐标或产能。域外煤炭输入点、原版采矿工厂与标准加工厂用于构成游戏货物链。

[国家发展改革委马鞍山历史介绍](https://cjjjd.ndrc.gov.cn/gongzuodongtai/yanjiangyaowen/anhui/202409/t20240912_1392976.htm)记录钢铁建设始于 1953 年、1956 年建市。本包“马鞍山矿区”城市是小聚落；钢铁点为游戏性提前配置。海上原油点是域外输入的抽象替代。

## 验证范围

离线校验：PNG IHDR 7169 × 7169 / 16 位 / 灰度；Lua 可解析，包含 {{TOWNS}} 城 {{INDUSTRIES}} 产业；坐标在图内，陆地/水上产业位置对应；点位保持间距；初始需求和加工链的必要输入有供应点。最终 PNG 的海域检查限定在海岸数据定义的海面，距岸至少 16 m 的水面上，长江口、上海外海、杭州湾、舟山北/东/南侧及甬江口外海属于同一连通分量；避免内河绕行掩盖海域断开。预览图经过查看。

尚未校验：游戏读取与保存、具体初始人数、城区就业/商业规模、树木资产生成、产业扩张占地、道路及船舶寻路、经济可玩性。静态链条完整不代表已完成游戏经济平衡测试。


## 版本差异

v0.2.0 将范围从 560 km 收至 350 km，保留南京—宁波走廊；DEM 从 zoom 10 提升至 zoom 12，工作网格从 3585 提升至 7169。原始高程采样更细，但海岸与湖形仍使用 Natural Earth 概化数据；没有把水系补绘的概化程度冒称为新的测绘精度。地形、航道加宽、生态分布与城市放置均重新计算。

v0.3.0 扩展至 380 km 并顺时针旋转 10°，将舟山（定海）、舟山主岛、朱家尖及邻近海域纳入。保留原有 16 城和 32 个产业，增加定海城市及 W04 舟山近海渔场。全部复用旧版 1806 张 zoom 12 高程瓦片和三份 Natural Earth 文件，仅补下载 1056 张瓦片；派生地形重新生成。

v0.3.1 保持范围、高程编码、水位、城市、产业和生态分布，补充“预览后仍需点击导入”的检查步骤、产业名称恢复命令及生态灰度说明。用户反馈的游戏日志存在生态应用记录，却缺少高度图替换记录；安装的 PNG 与 v0.3.0 发布包 SHA256 一致，约 27.4% 的像素低于 0 m。这支持“高度图未实际应用”的判断，尚未通过游戏导出地形最终确认。当前本地检出缺少原始缓存，按旧清单补齐缺失来源并核对 SHA256；没有删除旧缓存或改用旧派生高程。
