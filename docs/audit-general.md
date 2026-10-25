# 通用个人 Skill 审查

审查日期：2026-10-25。共 39 项，全部复制为脱敏副本；其中 3 项有明确运行适配要求。原安装目录未修改。

36 项能对应到 [mattpocock/skills](https://github.com/mattpocock/skills) 的公开源码，已核实 MIT 许可，并在每个 Skill 内保留 LICENSE 和 PROVENANCE.json。比对参考版本为 `5beb35b040e3de97e54fa9e386d7e42d15c295c2`；这不代表本机最初安装的版本。

本机自建的 compile-coordinator、resolving-merge-conflicts 仅作个人私有归档，未新增开源许可。git-workflow 保留本机声明的作者和 MIT 字段；原上游当前返回 404，因此记录为待核实来源、仅个人私有归档。

未发现真实凭据、个人绝对路径、内网地址或账号信息。git-workflow 的公司 GitLab 示例已替换为保留域名 git.example.com。空白占位符、示例 API 路由和公开上游来源链接予以保留。

状态 `needs_adaptation` 的文件同样可以存入个人私有仓库；该状态表示换到目标客户端使用前需检查依赖。此处没有安装软件、执行账号操作或修改原 Skill。

| Skill | 状态 | 来源 | 运行依赖与注意事项 |
| --- | --- | --- | --- |
| ask-matt | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 跨 Skill：code-review, codebase-design, diagnosing-bugs, domain-modeling, grill-me, grill-with-docs, grilling, handoff, implement, improve-codebase-architecture, prototype, research, resolving-merge-conflicts, setup-matt-pocock-skills, tdd, teach, to-questionnaire, to-spec, to-tickets, triage, wait-what, wayfinder, wizard, writing-for-agents |
| claude-handoff | needs_adaptation | mattpocock/skills；MIT 已核实；本机衍生版本 | 需要本机安装并登录 Claude CLI；它交接到 Claude 后台代理，不能直接视作 Codex 原生交接。 |
| code-review | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 跨 Skill：setup-matt-pocock-skills |
| codebase-design | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 无额外运行依赖记录 |
| compile-coordinator | included | 本机个人来源；仅个人私有归档，未授予新增开源许可 | Python 3 standard library；macOS or Linux |
| diagnosing-bugs | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 无额外运行依赖记录 |
| domain-modeling | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 无额外运行依赖记录 |
| git-guardrails-claude-code | needs_adaptation | mattpocock/skills；MIT 已核实；本机衍生版本 | 操作目标是 Claude Code 的 hook 配置，需要 Claude Code；不适用于 Codex 原生 hook。 |
| git-workflow | included | 本机声明作者与 MIT；上游当前无法核实；仅个人私有归档 | Git；GitHub CLI (gh)；GitLab CLI (glab, optional) |
| grill-me | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 跨 Skill：grilling |
| grill-with-docs | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 跨 Skill：domain-modeling, grilling |
| grilling | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 无额外运行依赖记录 |
| handoff | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 无额外运行依赖记录 |
| implement | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 跨 Skill：code-review, tdd |
| implement-spec | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 跨 Skill：code-review |
| improve-codebase-architecture | included | mattpocock/skills；MIT 已核实；本机衍生版本 | Browser for HTML report；Optional public Mermaid and Tailwind CDN |
| loop-me | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 跨 Skill：grilling |
| migrate-to-shoehorn | included | mattpocock/skills；MIT 已核实；本机衍生版本 | Node.js package manager；@total-typescript/shoehorn；TypeScript |
| prototype | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 无额外运行依赖记录 |
| research | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 无额外运行依赖记录 |
| resolving-merge-conflicts | included | 本机个人来源；仅个人私有归档，未授予新增开源许可 | 无额外运行依赖记录 |
| retro | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 跨 Skill：writing-for-agents |
| scaffold-exercises | needs_adaptation | mattpocock/skills；MIT 已核实；本机衍生版本 | 依赖目标课程项目提供 pnpm ai-hero-cli internal lint；其他项目需替换校验入口。 |
| setup-matt-pocock-skills | included | mattpocock/skills；MIT 已核实；本机衍生版本 | GitHub CLI or GitLab CLI when selected; local Markdown alternative available |
| setup-pre-commit | included | mattpocock/skills；MIT 已核实；本机衍生版本 | Node.js package manager；husky；lint-staged；prettier |
| setup-ts-deep-modules | included | mattpocock/skills；MIT 已核实；本机衍生版本 | TypeScript；Node.js package manager；dependency-cruiser |
| tdd | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 跨 Skill：code-review, codebase-design |
| teach | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 无额外运行依赖记录 |
| to-questionnaire | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 无额外运行依赖记录 |
| to-spec | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 跨 Skill：setup-matt-pocock-skills |
| to-tickets | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 跨 Skill：setup-matt-pocock-skills |
| triage | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 跨 Skill：domain-modeling, grilling, setup-matt-pocock-skills |
| wait-what | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 无额外运行依赖记录 |
| wayfinder | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 跨 Skill：domain-modeling, grilling, prototype, research, setup-matt-pocock-skills |
| wizard | included | mattpocock/skills；MIT 已核实；本机衍生版本 | Bash；Optional GitHub CLI for GitHub secrets |
| writing-beats | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 无额外运行依赖记录 |
| writing-for-agents | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 无额外运行依赖记录 |
| writing-fragments | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 无额外运行依赖记录 |
| writing-shape | included | mattpocock/skills；MIT 已核实；本机衍生版本 | 无额外运行依赖记录 |

按条目的详细依赖、脱敏动作和来源限制见 [audit-general.json](audit-general.json)。逐文件原始摘要与公开版本对比结果见各 Skill 的 PROVENANCE.json。

校验范围：所有文本文件扫描；JSON、YAML 与 Skill frontmatter；真实支持文档相对链接；Shell 语法与 Python 语法。示例中的目标项目路径不当作包内链接要求。没有把离线检查写成账号或网站端验收。
