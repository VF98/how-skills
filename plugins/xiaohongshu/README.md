# 小红书：Skill + MCP Plugin

这是 `personal-skills` 集合中的一个项目。Skill 描述何时使用和如何操作；MCP 执行搜索、文稿和平台动作；Plugin 把这些文件、配置和依赖组织为同一个可迁移包。

| 能力 | 实现 | 本包状态 |
| --- | --- | --- |
| 搜索 / 读取笔记 | 可选上游 Go MCP | 源码已收录；需单独构建、登录和配置，未在本轮实测 |
| 文稿编辑 / 版本 / 本地预览 | Python 本地 MCP | 现用实现的脱敏副本；离线测试覆盖 |
| 配图上传 / 同条图文草稿保存重开 | Python 本地 MCP | 源码已收录；新机器需本人登录并重新验收 |
| 最终发布图文 | 可选上游 Go MCP | 源码已收录；需明确授权，未在本轮实测 |

本地草稿与可选发布是两个独立后端。上游不直接读取本地浏览器原生草稿 ID；若获授权发布，应从本地文稿取出审阅后的内容与图片，再交给上游。保持两套登录和状态独立。

## 使用

默认 `mcp.json` 仅启用本地 stdio 服务，通过 `${PLUGIN_ROOT}` 定位文件，不含机器绝对路径。兼容清单在 `.codex-plugin/plugin.json` 和 `.mcp.json`。依赖 Python 3.11+ 与 macOS 已安装的 Chrome。

```bash
python3 scripts/run.py doctor
python3 scripts/run.py tools
python3 scripts/run.py isolated-status --capture-login
```

`doctor` 不打开浏览器；第三条会启动专用无界面浏览器并生成官方登录截图，需要用户本人手机确认。打包过程不运行第三条。

其他客户端如果不支持 `${PLUGIN_ROOT}`，复制示例到客户端自己的本地配置并替换为安装位置，保留在仓库外。只复制 Skill 时，需要同时保留本插件的 `docs/`、MCP 源码和运行入口，或预先配置对应服务。

搜索、最终发布的构建和配置见 [上游组件](docs/upstream.md)；本地后端详见 [说明](docs/local-backend.md)。源码归属与许可证见 `NOTICE`、`LICENSE`、`upstream.lock.json`。

原文稿、图片、Cookie、profile、截图和验收日志均未打包。本仓库没有安装或替换当前已运行服务，也没有连接账号进行搜索、上传或发布。

清单与本地 stdio 格式参考 [OpenAI 本地插件文档](https://developers.openai.com/plugins/deploy/desktop-only)。
