# logi-codex development entry

## 开发导航

- 动作和宿主接入：[CodexActionRingPlugin/src](CodexActionRingPlugin/src/)；契约与图标回归：[CodexActionRingPlugin/tests](CodexActionRingPlugin/tests/)。
- 构建、打包、校验的现行命令见 [README](README.md) 的 Build and test；工具原件在 [CodexActionRingPlugin/tools](CodexActionRingPlugin/tools/)。
- 验证：`check`（运行 `scripts/check`：README 的 Contracts、IconSystem 测试，装有 dotnet 时再构建并跑 .NET 测试项目；未装 dotnet 时明确跳过）。
- 源码检查与 Options+ 中真实环形菜单、快捷键和接收端效果分别验收。`artifacts/` 是打包产物，不能替代源码修改。
实现、评审或验收前读相关 [lessons](lessons.md)；出现可复用的纠正或漏验时更新原条目。
