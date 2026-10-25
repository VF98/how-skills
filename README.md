# Personal Skills

个人 Skill 与 Plugin 集合，小红书是其中一个项目。只收录已完成来源与脱敏审查的内容；未登记条目保留在本地，不随提交或导出发布。归档不会安装或替换现用 Skill/MCP。

36 个外部 Skill 来自 Matt Pocock 的 [skills 集合](https://github.com/mattpocock/skills)，包括 [grill-me](skills/grill-me/SKILL.md)。它们保留原作者、MIT LICENSE、本机修改记录和可见来源说明；完整归属见 [第三方来源总表](THIRD_PARTY_NOTICES.md)。

- `skills/`：40 个可作个人私有归档的通用或个人 Skill，保留原调用策略、配套脚本、来源和许可证。3 个仍需目标环境适配，不代表已可开箱运行。
- `plugins/xiaohongshu/`：完整小红书项目包，含 2 个 Skill、本地 Python MCP，以及锁定版本的可选 Go 搜索/发布 MCP 源码。
- `docs/`：53 个原有个人 Skill 的逐项脱敏审查；其中 13 个业务项未复制，列明后续改造或暂缓原因。
- `catalog.json`：个人条目与宿主管理技能的索引。内置/已安装第三方技能只登记，不重复打包。

## 选择 Skill 还是 Plugin

普通流程知识使用单独 Skill。小红书需要浏览器操作和 MCP 运行时，使用 [小红书 Plugin](plugins/xiaohongshu/README.md) 作为迁移单元，里面同时包含可单独阅读的 Skill。

小红书本地组件负责文稿、预览、配图上传和同条草稿保存；当前隔离后端不执行消费者搜索，也没有最终发布工具。可选上游提供搜索、读取及上传发布源码，本轮没有构建、登录或实测。发布会新建笔记，不能接管本地浏览器草稿 ID。

## 使用与迁移

在目标客户端按需安装 `skills/<name>`，保留同目录下的 supporting files。原有显式/自动触发策略原样保留。不要把所有技能一次装入每个项目；Claude CLI、课程文件、编译环境等依赖见 [通用审查](docs/audit-general.md)。

小红书按插件的 README 配置本地 stdio MCP，Portable 清单使用 `${PLUGIN_ROOT}`。新机器由本人登录，运行数据和登录态放在源码树之外；不要从原机器迁移 Cookie 或整个 profile。

## 检查与导出

新增与更新流程见 [CONTRIBUTING.md](CONTRIBUTING.md)，Agent 维护入口为 [AGENTS.md](AGENTS.md)。首次验证需安装 `requirements-dev.txt` 中的开发依赖。

```sh
python3 scripts/validate_repo.py
python3 scripts/check_export.py
python3 scripts/package.py
```

导出基于 Git 暂存区中的文件内容，排除历史、缓存和未暂存运行数据。压缩包输出到仓库外的同级 `personal-skills-exports/`。修改源码后先重新暂存再检查和导出。

上传前对实际 Git 暂存快照再次审计，使用 GitHub noreply 邮箱作为提交身份，并确认目标仓库保持私有。本次首次提交前复审见 [上传前审计](docs/pre-push-audit.md)。

## 审查与归属

[文档导航](docs/index.md) · [仓库布局](docs/repository-layout.md) · [个人 Skill 总览](docs/review-summary.md) · [通用组](docs/audit-general.md) · [业务组](docs/audit-business.md) · [来源核验](docs/source-verification-20261025.md) · [脱敏范围](docs/redaction.md) · [验证记录](docs/verification.md)

根 [LICENSE](LICENSE) 对本仓库原创维护脚本和整理文档采用 MIT。第三方 Skill 保留各自原许可，小红书组件保留 Apache-2.0；未明确授权的旧内容仍只作私人归档，具体范围见 [LICENSES.md](LICENSES.md)。
