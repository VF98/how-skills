# How Skills 使用指南

公开仓库：[VF98/how-skills](https://github.com/VF98/how-skills)。这是个人实际使用内容的整理集合，包含第三方公开 Skill 的本机衍生版、个人流程与带运行时的 Plugin。

## 先从一个 Skill 开始

```sh
git clone https://github.com/VF98/how-skills.git
cd how-skills
```

从 `skills/` 选择当前任务需要的一项，阅读其 SKILL.md，再按所用客户端的技能安装方式加载整个目录。保留 agents 元数据、支持脚本、参考文件、LICENSE 与 PROVENANCE；不要只拷一段正文。

推荐的起点是 [grill-me](../skills/grill-me/SKILL.md) 与 [grilling](../skills/grilling/SKILL.md)。前者是简短入口，实际会调用后者，因此两个目录一起保留。安装到客户端后，可以提出这样的请求：

> 用 grill-me 帮我把这个需求问清楚，先讨论目标、约束和未确定的部分。

希望测试先行时看 [tdd](../skills/tdd/SKILL.md)，维护 Agent 指令时看 [writing-for-agents](../skills/writing-for-agents/SKILL.md)。这些条目来自 Matt Pocock 的公开 skills 集合，原 MIT、署名与本机差异都保留。

各条目的 CLI、课程材料和其他外部依赖见 [通用审查](audit-general.md)。归档和结构校验通过，不等于每项都已适配你的机器；其中三个条目仍明确标注需要运行适配。

## 需要小红书能力时用完整 Plugin

完整目录为 [plugins/xiaohongshu](../plugins/xiaohongshu/README.md)，其中包含两个 Skill、MCP 配置、Python 本地后端与可选的 Go 上游源码。整体保留该目录，避免相对链接和运行入口丢失。

本地后端依赖 macOS 已安装的 Chrome 与 Python 3.11+。从该 Plugin 目录先做环境检查：

```sh
python3 scripts/run.py doctor
python3 scripts/run.py tools
```

这两条不会登录平台或上传素材。后续使用按 Plugin README 处理官方扫码登录及客户端 MCP 连接配置。

- 本地文稿：创建、修改、保留版本、生成离线预览。
- 平台图文草稿：首次配图上传、沿用同一原生草稿 ID 修改标题/正文、保存和重开；目标环境需本人登录并验收。
- 搜索和最终发布：可选上游 Go MCP，源码已收录，需要单独构建、配置和登录；本分发包没有对其做真实搜索或发布验收。

默认 MCP 只启用本地 Python 服务。两套后端独立登录，也不共享原生草稿 ID。已有平台图片替换/排序尚未实现。需要发布时，另行确认具体账号、稿件和素材。

## 来源与许可

36 个外部 Skill 保留 Matt Pocock 的 MIT 原文；小红书组件保留 Apache-2.0。根 MIT 只覆盖 [LICENSES.md](../LICENSES.md) 指定的原创维护材料；部分旧条目未新增开源授权，公开可读并不表示全仓内容都能统一按 MIT 再分发。

查看 [第三方来源总表](../THIRD_PARTY_NOTICES.md) 和具体目录的 PROVENANCE.json 再决定如何采用。不要把引入内容标成自己的原作。

## 修改和验证

贡献与维护流程见 [CONTRIBUTING.md](../CONTRIBUTING.md)。维护验证器、暂存区脱敏检查和导出脚本分别负责结构/来源、实际准备提交的内容，以及可迁移压缩包；这些检查不会执行全部已归档 Skill。
