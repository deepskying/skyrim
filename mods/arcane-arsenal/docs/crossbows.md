# 异构弩：0.47.0

四把弩的基础伤害为 95、Speed 为 1.4、重量为 14。Speed 是武器参数，实际射击间隔仍受装填动画影响。

| 名称 | EditorID | 插件内武器编号 | 造型 / 粒子 |
| --- | --- | --- | --- |
| 余烬·折翼 | AAcrossbowred | 000A19 | 叠片弩翼、三角碎光 |
| 流萤·萦弧 | AAcrossbowgreen | 000A1C | 双弧弩翼、弯月微光 |
| 寒汐·并轨 | AAcrossbowblue | 000A1F | 并列导轨、细线碎光 |
| 梦隙·偏枢 | AAcrossbowpurple | 000A22 | 非对称翼、菱形碎光 |

试武箱 `AAHeteromorphicCrossbowsChest`（插件内 000A24），包含四把弩和 200 钢弩箭。使用 `help "AAHeteromorphicCrossbowsChest" 4` 查询游戏加载后的完整编号，再 `player.placeatme <编号> 1`。

## 构建与验证

1. Python 执行 `source/prepare_crossbow_reference.py`，从本机游戏 BSA 提取原版弩参考到 build。
2. 便携 Blender 运行 `source/build_crossbows.py -- <key>`，四个 key 见表格。模型暂存到 build/crossbows-base；源文件与实际几何预览在 art/crossbows。
3. Blender 执行 `source/build_aries_particles.py -- --crossbows`，输出运行模型。六处原生粒子挂点随弩翼骨骼运动，每处容量 12。
4. Blender 执行 `source/verify_crossbows.py` 与 `source/verify_aries_particles.py -- --crossbows`；Python 对每个 key 执行 `source/verify_draw_particles.py <key>`。
5. Python 运行 `source/build_plugin.py`、`source/verify_plugin.py`，再使用 SSEDump 对独立测试目录的插件执行 `-check`。
6. 运行 `source/package_mod.py`、`source/install_mod.py`（游戏需关闭），最后 `source/sync_spid.py` 和 `--check`。

保留原版十个骨骼、七组动画控制器、CrossbowProject.hkx 行为、WeaponBow 挂点及 Havok 设置。可见几何为原创，碰撞范围重新拟合。弩弦为连续网格，中心混合左右弦骨权重，避免装填时中间断开。

插件增加 Update.esm 和 Dawnguard.esm 主文件后，自索引从 1 调整为 3。全部旧插件内编号不变；旧 WEAP/WNAM、COBJ/CNAM、CONT/CNTO、QUST/VMAD 与 SEQ 中的自身引用按字段更新，禁止全文件盲替换字节。新增局部编号 A18–A24，下一编号 A25。

模型预览使用便于观察轮廓的预览材质，不是游戏实拍。离线检查不能代替第一/第三人称装填、射击、收武器与 ENB 亮度复测。
