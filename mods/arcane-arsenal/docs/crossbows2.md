# 第二组异构弩 · 0.50.0

攻击力 95、Speed 1.4、重量 14，沿用原版钢弩箭与黎明守卫装填行为。

| 名称 | EditorID | 插件内武器编号 | 造型和粒子 |
| --- | --- | --- | --- |
| 余烬·破垒 | AAcrossbow2red | 000B81 | 宽厚三角镂空框架、三角碎光 |
| 流萤·回缭 | AAcrossbow2green | 000B84 | 完整螺旋卷翼、弯月微光 |
| 寒汐·叠汐 | AAcrossbow2blue | 000B87 | 上下分层弩翼和竖向连接、矩形碎光 |
| 梦隙·离枢 | AAcrossbow2purple | 000B8A | 不对称分节翼和能量细线、方形碎光 |

`AAHeteromorphicCrossbowsChest` 保持原编号 000A24，新生成的试武箱包含两组八把弩及 200 支钢弩箭。旧箱子可能不刷新，使用控制台 `help "AAHeteromorphicCrossbowsChest" 4` 查询完整加载编号并重新生成。

## 结构与兼容

沿用十个原版骨骼、七组动画控制器、BGED 行为、碰撞类别以及连续弩弦中心权重。第二组用宽面倒角梁构成主体；蓝色竖直连接的管状亮边使用稳定的截面轴，避免竖向零面积三角面。粒子随六个弩翼位置运动，单挂点容量 12，保持已有低亮度标准。

保留 0.49.1 的法杖加载顺序修复、DLL 和所有旧武器。新增 STAT/WEAP/COBJ 记录 B80–B8B，未重用旧编号。ESP 仍带 ESL 标记，三个官方主文件和自身索引均不变。

## 重建

先按 `docs/crossbows.md` 准备参考。Blender 对四个 `crossbow2*` key 执行 `source/build_crossbows.py -- <key>`；几何由 `source/crossbows2_geometry.py` 生成。之后执行：

- Blender：`source/build_aries_particles.py -- --crossbows2`
- Blender：`source/verify_crossbows.py -- --crossbows2`
- Blender：`source/verify_aries_particles.py -- --crossbows2`
- Python：逐个 key 执行 `source/verify_draw_particles.py <key>`
- Python：`source/build_plugin.py`、`source/verify_plugin.py`
- SSEDump：`-check` 验证包含三个主文件的独立目录中的插件。

使用打包、安装及 SPID 同步脚本完成发布。游戏内第一/第三人称握持、装填、瞄准和发光仍需用户复测；Blender 图仅为真实几何预览。

0.50.0 的 SSEDump 检查没有新增错误。0.49.1 基线已有四个法杖 PROJ 的 FULL 顺序和 NAM1 缺失报错，本次逐条比较结果一致，未修改这些记录；不能将全插件检查描述为零错误。对比记录见 `build/crossbows2-regression.json`。
