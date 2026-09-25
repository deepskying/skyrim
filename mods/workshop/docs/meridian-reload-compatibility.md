# 死亡读档后出现上下黑边：本地兼容性排查

2026-09-13，装备工坊 1.4.4 / MeridianUI 1.5.0。

症状是整个游戏画面上下出现黑边，打开 Esc 系统菜单后恢复。耐久常显日志已正常发送装备，因此不是之前的界面初始化握手故障。

MeridianUI 日志在每次读档时记录 `BoundGameRenderTarget` 从 2560×1440 切到 2048×2048，再切回。`BeforeRendererEnd` 路径使用当前绑定的渲染目标，并据此通知浏览器改变尺寸；它可能读到加载阶段的临时目标。这是当前排查线索，尚未通过游戏内复测证明是唯一原因。

本机 MeridianUI.ini 显式设置了 `BeforeRendererEnd`，但 SkyrimUpscaler.ini 设置为 FSR2（`mUpscaleType = 1`）。已在 MO2 的「基础模组-MeridianUI」中恢复默认合成时机：

```ini
[Compatibility]
CompositorTiming=AfterRendererEnd
```

此模式在游戏 renderer-end 调用后使用交换链后缓冲作为界面目标。原配置和故障日志已备份到 MO2/backups/MeridianUI-before-reload-compatibility-*。未修改工坊 DLL、存档、ENB 或 Upscaler 设置。

重启后需复测：

1. 确认 MeridianUI.log 的 compositor timing 为 AfterRendererEnd，目标为 SwapChainBackbuffer。
2. 确认耐久常显及工坊正常显示；连续死亡读档，期间不按 Esc，检查黑边是否消失。
3. 若发生界面不可见或不同 D3D11 device 的拒绝日志，保留日志并恢复备份配置，继续检查底层渲染兼容性。

此为本地兼容配置，不随工坊安装包覆盖公共 MeridianUI 配置。以后若启用 DLSS 5 / Neural Reconstruction，需重新验证；上游的 BeforeRendererEnd 专用兼容路径不能一概禁用。
