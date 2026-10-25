# 仓库布局与参考

这个仓库同时保存独立 Skill 和需要本地运行时的 Plugin，沿用各自的安装单元。

```text
personal-skills/
  README.md                    集合入口
  AGENTS.md                    仓库维护约定
  CONTRIBUTING.md              新增与更新流程
  LICENSE                      仓库原创维护材料的 MIT
  LICENSES.md                  根许可范围与目录例外
  THIRD_PARTY_NOTICES.md        原作者与来源总表
  catalog.json                 条目和收录状态索引
  skills/<name>/
    SKILL.md                   能力入口
    agents/openai.yaml         可选界面与调用策略
    PROVENANCE.json            原仓库、本机差异、许可依据
    LICENSE                    已取得的原许可
    scripts/ references/       按实际需求保留的支持文件
  plugins/xiaohongshu/
    plugin.json mcp.json       可迁移清单
    skills/                    该 Plugin 的两个 Skill
    xhs_local/                 本地 Python MCP
    vendor/                    锁定的可选上游源码
  docs/                        来源、依赖、隐私和验收说明
  scripts/                     只用于维护、验证和导出的脚本
```

40 个独立 Skill 保持单层目录，方便按目录复制；两个小红书 Skill 留在 Plugin 中，使相对文档链接和运行入口随包迁移。分类通过索引表达，避免只为展示调整已有名字和调用关系。

## 实际参考的公开仓库

已取得并核验 [mattpocock/skills 的固定快照](https://github.com/mattpocock/skills/tree/5beb35b040e3de97e54fa9e386d7e42d15c295c2)：

- [README](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/README.md) 将可用 Skill 列表、安装方式和调用关系分开说明。
- [仓库维护约定](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/CLAUDE.md) 要求新增和改名时同步文档/清单，并明确区分调用方式。
- [grill-me 的目录](https://github.com/mattpocock/skills/tree/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/productivity/grill-me) 展示了 SKILL.md 与代理元数据的组合；[原 LICENSE](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/LICENSE) 为 MIT。

这里采用其索引可导航、调用策略明确、文档与实际能力同步的做法。它的分组层级、插件市场和发布流程服务于其自身分发方式，本集合按实际安装单元保留当前结构。

技能文件组织也按本机可用的 Skill Creator 规范处理：短入口、按需参考、可选 scripts/references/assets 和 agents 元数据。小红书清单依据上一轮读取的 [OpenAI 本地插件文档](https://developers.openai.com/plugins/deploy/desktop-only)。

## 其他可继续对照的公开参考

[Agent Skills 规范](https://agentskills.io/specification)、[OpenAI skills](https://github.com/openai/skills)、[Anthropic skills](https://github.com/anthropics/skills) 是后续兼容性核查入口。本轮尝试读取这些站点时网络失败，未以未取到的网页内容作为新的格式结论；当前验证范围以本仓库文档和已核实快照为准。
