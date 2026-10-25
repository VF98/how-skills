# 可选搜索与发布后端

本插件收录了 [xpzouying/xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp/tree/a5c8f7799980ba1fdd501999843eb2d17e4c9a9f)
的 v2.5.5 源码选集，提交为 `a5c8f7799980ba1fdd501999843eb2d17e4c9a9f`，
许可证为 Apache-2.0。原始许可保留在 `vendor/xiaohongshu-mcp/LICENSE`；
逐文件 SHA-256 见 `../upstream.lock.json`。选入的上游文件没有修改。

这是可选的第二个 MCP，服务名建议为 `xiaohongshu-upstream`。
现用 Python 本地助手负责文稿编辑、上传和同 ID 草稿保存；这份上游提供搜索和最终发布。
本次仅完成源代码及配置整理，没有启动上游、下载浏览器、登录、搜索或发布。

## 能力与边界

| 任务 | 工具 | 本包验证状态 |
| --- | --- | --- |
| 登录状态、官方扫码 | `check_login_status`、`get_login_qrcode` | 源码收录，运行未验收 |
| 搜索与读取 | `search_feeds`、`get_feed_detail`、`list_feeds` | 源码收录，真实检索未验收 |
| 账号与主页 | `user_profile`、`get_my_profile` | 源码收录，运行未验收 |
| 上传并发布图文 | `publish_content` | 源码收录，未做任何真实发布 |
| 上传并发布视频 | `publish_with_video` | 上游附带能力，本轮未启用 |
| 原生草稿编辑、同 ID 发布 | 无 | 不能用这组工具实现 |
| 互动与通知 | 评论、回复、点赞、收藏、通知工具 | 上游附带能力，按具体任务另行授权 |

上游注册了 18 个 MCP 工具。`publish_content` 包含素材上传和最终发布，不能用它代替“只上传到草稿”。
它不接受本地助手的文稿 ID，也不会接管现用 Chrome profile 中的同一条草稿。

上游自带浏览器下载器，首次运行可能下载约 140–190 MB 的独立浏览器；
这与 Python 助手使用已安装 Google Chrome 的方式不同。上游还包含代理、浏览器指纹和互动选项，
本包保持锁定源码不变，操作 Skill 不指示通过这些选项绕过风控。
遇到平台拦截应停止并报告。两套会话、Cookie 和草稿存储相互独立。

## 后续本机启动方式

本轮没有 Go 运行时，因此未构建或运行。锁定 `go.mod` 声明 Go 1.24.0；
依赖版本由 `go.mod` 和 `go.sum` 固定。以下为具备 Go 的环境中手动启用时的命令，
从 `vendor/xiaohongshu-mcp/` 运行：

```sh
XHS_UPSTREAM_DATA="${XDG_DATA_HOME:-$HOME/.local/share}/personal-skills/xiaohongshu-upstream"
mkdir -p "$XHS_UPSTREAM_DATA"
chmod 700 "$XHS_UPSTREAM_DATA"
export COOKIES_PATH="$XHS_UPSTREAM_DATA/cookies.json"
umask 077
go build -o "$XHS_UPSTREAM_DATA/xiaohongshu-mcp" .
"$XHS_UPSTREAM_DATA/xiaohongshu-mcp" -headless=true -port 127.0.0.1:18060
```

显式指定 `COOKIES_PATH` 避免读取上游的当前目录或旧临时目录会话。
上游源码写 Cookie 的模式参数为 0644，因此启动命令设置 `umask 077`，新建文件有效权限为 0600；
已有 Cookie 文件需要保持私有权限。运行状态、媒体、Cookie 和日志均不纳入仓库。

上游原默认 `-port :18060` 会监听非限定接口；上面的命令显式限定 loopback。
`mcp.upstream.example.json` 也仅连接 `http://127.0.0.1:18060/mcp`，它不在默认 `mcp.json` 中自动启用。
上游支持从环境变量 `AUTH_TOKEN` 读取可选 Bearer 鉴权；如需配置，在本机凭据存储和客户端设置中处理，
不要把值写入仓库。不要通过 `-token` 命令参数传入真实凭据。

本机后端启动后，按客户端支持的方式合并示例 MCP 连接，再进行工具发现与 `check_login_status`。
如需登录，使用官方二维码，由用户本人扫码。先进行只读检索验收；
真实发布应有对具体账号、内容、素材和可见范围的授权，并单独验证结果。
服务监听成功或工具列出均不代表发布能力已经验收。

## 打包检查

本次从锁定 Git 对象提取 Go 源码和测试、`go.mod`、`go.sum`、嵌入浏览器版本文件与 `LICENSE`，
未复制 `.git`、上游账号配置、现有用户素材、Cookie、浏览器二进制或历史数据。
上游旧版 `post-to-xhs` Python Skill 未纳入，避免与本包以 Go MCP 为入口的工作流重叠。
源码字节哈希与锁定提交一致；本包增加的 `NOTICE`、Skill 与说明属于包装材料。
