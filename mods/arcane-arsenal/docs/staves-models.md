# 幻律兵装 · 几何法杖模型 0.2.0

根据用户反馈，四把法杖改用既有武器的纯几何设计：纯色实体、发光倒角、简洁长杆与开放框架。移除上一版的皮革缠绕、晶叶、小挂饰和金属反光材质。名称继续沿用。

| 名称 | 文件键 | 新版造型 |
| --- | --- | --- |
| 余烬·裂冕 | staffred | 三片错落几何冠翼、菱形核心、上杖菱形框 |
| 流萤·盘枝 | staffgreen | 两层开放旋环、菱形中心、立体双带 |
| 寒汐·悬衡 | staffblue | 前后错层的长短矩形框、悬浮方块与短条 |
| 梦隙·缺环 | staffpurple | 厚实开放多边环、内层断菱框与菱形中心 |

## 交付

- `art/staves-geometric/`：四个内嵌贴图的 Blender 工程、各自预览、`staves-lineup.png` 合照及 `staves-heads.png` 杖头细节。
- `models/staves-geometric/Data/`：八个 NIF（每把各一份第一、第三人称）及六张 DDS。
- `models/staves-geometric/verification.json`：导出验证和文件 SHA-256。
- `packaging/ArcaneArmory-Staves-Models-0.2.0.zip`：本版完整模型资源包。

预览图来自实际 Blender 模型渲染，不是生成式概念图，也不是游戏截图。上一版模型和 0.1.0 资源包仍单独保留。

## 材质与模型

每个模型只有 `AA_StaffBody` 和 `AA_StaffEdge` 两个刚性形状。材质、纯色贴图、法线与 glow map 直接沿用现有几何武器，去除镜面反光。主体 / 光边强度保持红 1.8 / 3.6、绿 2.25 / 4.5、蓝 2.25 / 5.4、紫 2.7 / 5.4。

沿用原版 Staff01 根坐标和 `WeaponStaff` 挂点，Y 为长轴。握柄在原点附近，掌心半径不超过 1.34 个模型单位。核心与内框静态悬置，尚无旋转、粒子或法术。

最终 NIF 使用下杖、握柄、上杖、杖头四段拟合碰撞盒，覆盖全部顶点；保留原版法杖刚体参数。碰撞简化了镂空。Blender 工程中隐藏的原版胶囊仅作导出模板，实际四盒碰撞由构建脚本写入 NIF；修改尺寸后需通过该脚本重新导出。

## 验证与阶段

八个 NIF 均重新导入，对比源模型双向顶点坐标，检查掌心截面、真实负空间、立体双带、材质类型 / 发光强度、贴图与既有武器的一致性、mipmaps、根挂点和碰撞覆盖。验证通过后才打包。

本次仅修改模型资产，尚未注册装备或配置法术，也未修改主集合 ESP、MO2 安装和 SPID。游戏内握持、遮挡、落地物理与 ENB 下的观感仍待下一阶段实测。接入装备时再统一注册记录、更新物品箱 / SPID 与正式发布。

## 重建

在仓库根目录依次运行：

```powershell
python mods/arcane-arsenal/source/prepare_staff_reference.py
& reference/bow-tools/blender-4.5.13-windows-x64/blender.exe -b --python-exit-code 1 --python mods/arcane-arsenal/source/build_staves.py
& reference/bow-tools/blender-4.5.13-windows-x64/blender.exe -b --python-exit-code 1 --python mods/arcane-arsenal/source/render_staves.py
& reference/bow-tools/blender-4.5.13-windows-x64/blender.exe -b --python-exit-code 1 --python mods/arcane-arsenal/source/verify_staves.py
python mods/arcane-arsenal/source/package_staves_models.py
```

使用现有 Blender 4.5.13、PyNifly 28.2、仓库内材质模板和本机原版参考。中间资源在 `build/staves-geometric`，验证后复制到 `models/staves-geometric`。包内源码需配合现有仓库使用；最终 NIF 不包含原版可见网格。
