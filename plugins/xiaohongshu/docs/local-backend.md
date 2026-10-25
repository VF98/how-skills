# 本地文稿与图文草稿

当前分发源码基于原个人适配器 v0.4.0，仅标准库 Python（建议 3.11+）和已安装的 macOS Google Chrome。新入口将运行状态置于 `~/.local/share/personal-skills/xiaohongshu`，也可用 `XHS_LOCAL_DATA` 或 CLI 的 `--data-dir` 指定独立目录。不要指向日常 Chrome profile。

MCP 默认入口为 `scripts/run.py mcp`，选用独立无界面后端。CDP 调试端点仅绑定 loopback 的随机端口，连接时核对专用进程和已登记 target。账号通过官方网页登录；二维码截图和浏览器 profile 只存在运行数据目录。

本包不带登录状态、文稿数据库、真实图片、草稿 ID、截图或历史验收日志。`doctor` 和状态工具报告源码能力，`live_verified=false`，不会将原账号验收当作新环境验收。

## 接口

16 个本地工具：`xhs_doctor`、`xhs_isolated_status`、4 个 `xhs_local_manuscript_*` 工具、7 个 `xhs_platform_draft_*` 工具，以及旧版 `xhs_search`、`xhs_read_note`、`xhs_creator_inspect`。后三个旧消费者/桌面入口在隔离模式下拒绝执行；`xhs_platform_draft_bind` 也拒绝绑定日常 Chrome。

本地文稿操作可以离线运行；平台同步首次上传授权图片，后续沿用同 ID 修改标题、正文与标签文字。保存后从官方列表重开并核对。中断恢复先检查同版本逐字段匹配，避免重复上传。

不包含最终发布、私密发布、定时发布、互动写入。现有图片替换/排序、平台话题实体、跨设备草稿同步和完整浏览器重启恢复不作为已验证能力。

## 本地检查

```bash
python3 scripts/run.py --help
python3 scripts/run.py doctor
python3 -m unittest discover -s tests -v
```

单元测试使用离线夹具或本地测试页面；不登录、不上传到平台，也不发布。历史诊断模块保留为源码，不在新环境自动运行。
