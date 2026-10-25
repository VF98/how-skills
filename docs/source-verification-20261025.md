# 外部 Skill 来源核验：2026-10-25

本次复核覆盖 36 项来自 Matt Pocock 公开 Skill 集合的本机衍生副本。下述内容差异以添加本仓库可见署名之前的副本为准；后续署名和元数据改动已另记入各目录的 PROVENANCE.json。使用本轮先前成功联网取得的公开源码快照，通过固定提交的 Git 文件树和文件内容逐项核对。追加联网复查未成功，因此不声明该比较提交仍是远端最新 main。

比较提交：`5beb35b040e3de97e54fa9e386d7e42d15c295c2`。这是本次核验的参考版本，**不是已查明的原始安装提交**。本机最初安装版本未记录。

## 许可与作者

公开来源为 [mattpocock/skills](https://github.com/mattpocock/skills)。[固定提交的 LICENSE](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/LICENSE) 使用 MIT License，原版权声明为 `Copyright (c) 2026 Matt Pocock`。

36 份副本各自附带的 LICENSE 均与该固定提交的原文逐字节一致。上游许可证 SHA-256：

`0e7ac423bf2c6e223b7c5b156f8cf72da49d748e56a1641402c31f22ad07dbb5`

MIT 许可允许复制、修改和分发，并要求保留原版权及许可声明。仓库整理者不能把外部 Skill 的原作者改成自己；本机修改应另外注明维护者和修改情况。合集的根许可证也不能覆盖或替代这些第三方文件的原始许可。

## grill-me 的准确归属与差异

- 原始项目与路径：[skills/productivity/grill-me/SKILL.md](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/productivity/grill-me/SKILL.md)。
- 归属：Matt Pocock 的公开 Skill 集合；并非本仓库整理者原创。
- 本机文档正文与参考版本一致，都是转到 grilling Skill 的简短入口。
- 本机 SKILL.md 删除了参考版本中的 disable-model-invocation: true 字段。
- [参考 agents/openai.yaml](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/productivity/grill-me/agents/openai.yaml) 与本机 YAML 均保留 allow_implicit_invocation: false；展示名称和简介仅有 YAML 引号风格变化。因此不能把该差异描述为已改成自动调用。
- 本机副本依赖同集合的 grilling Skill。两项均已归档。

建议来源表述：

> 来源：mattpocock/skills（Matt Pocock，MIT）。此处保存本机已安装的衍生副本；本次以固定提交 5beb35b040e3de97e54fa9e386d7e42d15c295c2 作比较，原始安装提交未知。保留原许可和版权声明；兼容调整与本机差异见 PROVENANCE.json。

## 36 项参考路径逐项核验

以下 reference_path 均在上述固定提交的 Git 文件树中存在 SKILL.md；所有条目的 reference_revision 均正确，目录内 LICENSE 均与上游一致。该检查证明来源映射及许可副本一致性，不证明本机衍生版与上游整个目录完全相同。

| 本地 Skill | 公开参考路径 | 路径 / 许可 |
| --- | --- | --- |
| ask-matt | [skills/engineering/ask-matt](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/ask-matt/SKILL.md) | 通过 / 一致 |
| claude-handoff | [skills/in-progress/claude-handoff](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/in-progress/claude-handoff/SKILL.md) | 通过 / 一致 |
| code-review | [skills/engineering/code-review](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/code-review/SKILL.md) | 通过 / 一致 |
| codebase-design | [skills/engineering/codebase-design](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/codebase-design/SKILL.md) | 通过 / 一致 |
| diagnosing-bugs | [skills/engineering/diagnosing-bugs](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/diagnosing-bugs/SKILL.md) | 通过 / 一致 |
| domain-modeling | [skills/engineering/domain-modeling](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/domain-modeling/SKILL.md) | 通过 / 一致 |
| git-guardrails-claude-code | [skills/misc/git-guardrails-claude-code](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/misc/git-guardrails-claude-code/SKILL.md) | 通过 / 一致 |
| grill-me | [skills/productivity/grill-me](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/productivity/grill-me/SKILL.md) | 通过 / 一致 |
| grill-with-docs | [skills/engineering/grill-with-docs](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/grill-with-docs/SKILL.md) | 通过 / 一致 |
| grilling | [skills/productivity/grilling](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/productivity/grilling/SKILL.md) | 通过 / 一致 |
| handoff | [skills/productivity/handoff](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/productivity/handoff/SKILL.md) | 通过 / 一致 |
| implement | [skills/engineering/implement](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/implement/SKILL.md) | 通过 / 一致 |
| implement-spec | [skills/engineering/implement-spec](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/implement-spec/SKILL.md) | 通过 / 一致 |
| improve-codebase-architecture | [skills/engineering/improve-codebase-architecture](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/improve-codebase-architecture/SKILL.md) | 通过 / 一致 |
| loop-me | [skills/in-progress/loop-me](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/in-progress/loop-me/SKILL.md) | 通过 / 一致 |
| migrate-to-shoehorn | [skills/misc/migrate-to-shoehorn](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/misc/migrate-to-shoehorn/SKILL.md) | 通过 / 一致 |
| prototype | [skills/engineering/prototype](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/prototype/SKILL.md) | 通过 / 一致 |
| research | [skills/engineering/research](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/research/SKILL.md) | 通过 / 一致 |
| retro | [skills/engineering/retro](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/retro/SKILL.md) | 通过 / 一致 |
| scaffold-exercises | [skills/misc/scaffold-exercises](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/misc/scaffold-exercises/SKILL.md) | 通过 / 一致 |
| setup-matt-pocock-skills | [skills/engineering/setup-matt-pocock-skills](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/setup-matt-pocock-skills/SKILL.md) | 通过 / 一致 |
| setup-pre-commit | [skills/misc/setup-pre-commit](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/misc/setup-pre-commit/SKILL.md) | 通过 / 一致 |
| setup-ts-deep-modules | [skills/in-progress/setup-ts-deep-modules](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/in-progress/setup-ts-deep-modules/SKILL.md) | 通过 / 一致 |
| tdd | [skills/engineering/tdd](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/tdd/SKILL.md) | 通过 / 一致 |
| teach | [skills/productivity/teach](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/productivity/teach/SKILL.md) | 通过 / 一致 |
| to-questionnaire | [skills/productivity/to-questionnaire](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/productivity/to-questionnaire/SKILL.md) | 通过 / 一致 |
| to-spec | [skills/engineering/to-spec](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/to-spec/SKILL.md) | 通过 / 一致 |
| to-tickets | [skills/engineering/to-tickets](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/to-tickets/SKILL.md) | 通过 / 一致 |
| triage | [skills/engineering/triage](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/triage/SKILL.md) | 通过 / 一致 |
| wait-what | [skills/productivity/wait-what](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/productivity/wait-what/SKILL.md) | 通过 / 一致 |
| wayfinder | [skills/engineering/wayfinder](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/wayfinder/SKILL.md) | 通过 / 一致 |
| wizard | [skills/engineering/wizard](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/wizard/SKILL.md) | 通过 / 一致 |
| writing-beats | [skills/in-progress/writing-beats](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/in-progress/writing-beats/SKILL.md) | 通过 / 一致 |
| writing-for-agents | [skills/productivity/writing-for-agents](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/productivity/writing-for-agents/SKILL.md) | 通过 / 一致 |
| writing-fragments | [skills/in-progress/writing-fragments](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/in-progress/writing-fragments/SKILL.md) | 通过 / 一致 |
| writing-shape | [skills/in-progress/writing-shape](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/in-progress/writing-shape/SKILL.md) | 通过 / 一致 |

逐文件 identical_files、different_files、local_only_files 以及原本机文件摘要已保存在对应 Skill 的 PROVENANCE.json。新整理修改应继续记录；不要将 reference_revision 改写为 original_install_revision。

## 验证边界

本记录没有修改 Skill、许可证、运行配置或上游仓库。当前联网复查受阻，只对已经取得的固定公开提交作确定性核验。对原始安装时间、原始安装提交、未记录的修改作者及远端分支后续变化，不作推断。
