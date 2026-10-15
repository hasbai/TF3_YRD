# 来源与制作口径

制作日期：2026-10-15。

## 导入格式

- [Transport Fever 3 官方地图尺寸](https://wiki.transportfever3.com/doku.php?id=gamemanual:mapsizes)：Gigantomaniac 方图 28.672 km，7169 px；通过 `experimentalMapFeatures` 开启。
- [官方地图编辑器](https://wiki.transportfever3.com/doku.php?id=gamemanual:gamemodes:mapeditor)：16 位 PNG、生态蒙版与城市产业 Lua 导入，以及保存地图流程。
- [官方产业与货物](https://wiki.transportfever3.com/doku.php?id=gamemanual:simulation:industriescargos)：温带产业类型、初始需求和原料链。
- [TPF3 Map Studio](https://github.com/sharpi13822/TPF3-Map-Studio)，读取源码提交 `8126e8c1a63a50f42980ebc908e97592bae2aac2`：
  - `src/heightmap/towns_export.py`：作者记录人口由中间规模因子控制，0.2 约 19 人、1 约 98 人；前后因子保留 1。
  - `src/heightmap/industries_export.py`：作者实测原版温带产业资源路径 `::/industries/<tag>/<tag>.con`。
  - `src/heightmap/biome_mask.py`、`docs/SPIELWISSEN.en.md`、`src/gui/heightmap_guide.py`：温带蒙版灰度区间、Biome 1 的树群及实际导入步骤。

本包借鉴已记录的格式和测试结论，独立制作地理、地形和布局；没有运行 Studio 的 Windows 图形软件，也没有把作者实测冒称为本包在游戏中的验收。

原生格式另核对本机游戏的 `base/content/gui.zip` 中 `gui/map_editor/map_editor.tl` 与 API 类型声明：高度图导入按钮会调用地形替换命令并记录 `Replacing terrain`；生态应用读取现有高度图。产业导入只复制位置、旋转、是否水上、资源路径和标签，不读取名称。包内的一次性名称命令使用 `Industry.construction`、`Construction.transf:getTransl()` 与 `api.cmd.makeEntitySetNameCmd`，按最终位置和资源路径匹配后改名。名称命令使用离线模拟检查；本版游戏验收状态见 `docs/游戏验收.md`。

## 高程

[Mapzen Terrain Tiles / AWS Open Data](https://registry.opendata.aws/terrain-tiles/)。实际下载 {{TILE_COUNT}} 张 zoom {{ZOOM}} Terrarium 瓦片，来自 `elevation-tiles-prod`，全部下载完成。RGB 解码公式为 `R×256 + G + B/256 − 32768`。

世界坐标中心：{{CENTER}}。地理内容顺时针旋转 {{ROTATION}}°，南京—舟山接近图中左上—右下对角线。实际四角（依次为图中左下、右下、右上、左上）：{{CORNERS}}。下载包围盒：{{BBOX}}，包围盒角部不属于实际地图。采用中心纬度的局部等距近似，水平压缩约 {{SCALE}} 倍；DEM 逐像素逆变换到经纬度采样，海岸、城市、产业和航道使用相同变换。

源瓦片在本区地面分辨率约 {{SOURCE_SPACING}} m/px。本版直接使用 7169 px 制作网格；实际地图约 {{REAL_SIDE_KM}} km，对应实地网格约 {{REAL_GRID_SPACING}} m。输出为游戏 4 m 采样网格，其密度不代表实地 4 m 测绘精度。

改动：轻微平滑；将陆地起伏缩至约 35%，为旧版的 3.5 倍；河岸在 48 游戏米内过渡到统一水面；单独雕刻海底、河床、湖盆；平整城市与产业位置。PNG 黑白编码范围为 −20—700 m，实际地形约 −12—{{MAX_TERRAIN}} m。

地形数据署名：Mapzen Terrain Tiles。Global GMTED2010 and SRTM terrain data courtesy of the U.S. Geological Survey.

Global ETOPO1 terrain data courtesy of the U.S. National Oceanic and Atmospheric Administration.

瓦片为多源融合，未逐像元鉴定底层来源。[Mapzen 数据署名说明](https://github.com/tilezen/joerd/blob/master/docs/attribution.md)。

## 海岸、湖泊、河流

[Natural Earth 10m Physical Vectors](https://www.naturalearthdata.com/downloads/10m-physical-vectors/)，固定源提交 `ca96624a56bd078437bca8184e78163e5039ad19`，使用 `ne_10m_land`、`ne_10m_lakes`。旧版河流文件继续保留在缓存，本版河道改用 OSM。其中“10m”表示 **1:1000 万制图比例尺**，不是 10 米精度。其数据为公共领域。[使用条款](https://www.naturalearthdata.com/about/terms-of-use/)。

湖泊和现代水库均保留，包括千岛湖；不再按 1950 年地貌排除水库。海岸和主要湖形来自 Natural Earth。

河流中心线来自 [Geofabrik 中国分省 OSM 提取](https://download.geofabrik.de/asia/china.html)：上海、江苏、浙江、安徽。使用 pyosmium 提取长江、黄浦江、吴淞江、富春江—钱塘江、甬江水系与曹娥江，保留原始折线节点。删除全部运河、太浦河、望虞河等人工直渠；没有数据的河段留空，不用直线或样条补齐。来源 URL、原始 PBF SHA256 与 OSM way ID 见 `data/waterways.geojson` 及包内源数据清单。中心线按游戏需要加宽，河宽不是实测河岸。

OSM 署名：© OpenStreetMap contributors，[ODbL 1.0](https://www.openstreetmap.org/copyright)。采用现代自然河流资料。太湖保留为独立湖泊。

植被不是遥感分类结果，而是按高程、低地、固定种子随机斑块及建设预留区制作的设计分布。用于重现“山林—平原—水岸”的总体关系。

温带生态灰度 26 对应 Biome 0 开阔草地。77 对应 Biome 1 草地树群，128 对应 Biome 2 深色草地。岸边使用深色草地作视觉过渡，不表示原生湿地分类。所报树群群落比例是蒙版区域比例，不是游戏实际树冠覆盖率。

## 城镇与人口

地图保留 1950 年开局，地形、城镇名称和中心点采用现代资料。城镇定位参考缓存 OSM 的 city、town 节点，节点链接记入布局数据及城市 CSV。张家港、德清、建德、上虞、余杭、浦口改用现今中心位置，另加入安吉。城镇及产业中源于 OSM 的坐标和地物资料按 ODbL 1.0 提供。

17 座主要城市的人口统一参考[芜湖市统计局发布的 2020 年长三角七普数据](https://tjj.wuhu.gov.cn/tjxx/tjfx/8340308.html)。每 8 万参考人口约对应 1 名游戏居民：上海约 311、苏州约 159、杭州约 149、南京约 116 人。参考值采用全市常住人口，包含下辖县市，仅用于游戏规模换算；其他城镇规模为设计估计。

## 产业

名称及原始位置参考现代企业、厂区、农场和园区，逐点来源记入布局数据及产业 CSV。游戏工厂类型用于表示主营产业，产能和供需按原版货物链配置。最终建筑会在原始点附近选择可建设位置，CSV 同时保留原始经纬度、落地点及偏移量。

产业中的 29 个陆地点采用 OSM 同名厂区、基地或地物坐标；三个渔场采用真实水域名称。原版黏土矿、砖厂分别表示建材矿物原料、陶瓷及墙材制造；棉花农场和煤矿表示相应原料供应。

海上原油输入平台保留在地图东缘约 500 游戏米处，代表域外输入。原料输入节点使用游戏对应资源工厂表示。

## 中文名字集

新建地图使用 `nameList = "::/names/china/china.names"`，显示语言使用 `zh_CN`。本机游戏的 `names/china/china.names.lua` 按显示语言选择中文或英文名单；两项需同时满足，后续生成的名称才使用中文。

原生城镇产业导入器不读取顶层名字集或语言字段。包内 `manifest.json` 记录必选设置，导入说明要求在新建地图时选择；名字集随游戏保存的地图保留。布局 Lua 不修改这两项设置。

## 验证范围

离线校验：PNG 为 7169 × 7169、16 位灰度；Lua 包含 {{TOWNS}} 城、{{INDUSTRIES}} 产业。坐标均在图内，陆地与水上产业位置对应，点位保持间距。初始需求和加工链有必要的供应点。

海域检查使用最终 PNG，并限定于海岸数据定义的海面。检查在距岸至少 16 m 的水面上进行。长江口、上海外海、杭州湾、舟山周边与甬江口外海属于同一连通分量。

道路使用游戏自带 Main Connections 功能，包内不生成道路。本版按用户要求只制作地图文件，不安装或操作游戏；游戏验收状态为未执行。

## 本版变化

v0.4.0 将高程比例从 10% 提至 35%，PNG 最高编码改为 700 m；使用 OSM 自然河流节点替换简化补绘，删除人工直渠和手绘西湖。城镇和产业按现代资料配置，保留 1950 开局，加入中文名字集设置要求。
