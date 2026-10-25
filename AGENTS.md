# 维护这个仓库

这里维护个人 Skill、Plugin 及其分发材料。`skills/` 下的工作流是归档内容；只有当前任务需要某项能力时才加载对应 Skill，避免因为它在仓库中就执行其安装、部署或发布步骤。

## 修改入口

- 独立 Skill 位于 `skills/<name>/`；目录名与 `SKILL.md` 的 `name` 一致，支持文件随目录保留。
- 带运行时的能力位于 `plugins/<name>/`；小红书的文稿后端和可选搜索发布后端保持各自的状态与验证范围。
- 新增或更新条目时按 [CONTRIBUTING.md](CONTRIBUTING.md) 处理来源、许可、依赖和目录规范。
- 修改第三方条目前读该目录的 `PROVENANCE.json` 和 `LICENSE`，保留原作者。比较提交与原始安装提交分别记录；原版本未知时明确标注未知。
- 保留已有 `agents/openai.yaml` 的调用策略。新增来源说明不应改变 Skill 工作流或隐式调用设置。

## 验证与交付

先运行 `python3 scripts/validate_repo.py`。只有改到小红书运行代码时才补跑其相关离线测试；真实登录、上传或发布按当前用户任务的授权处理，仓库维护本身不包含这些动作。

原始运行数据放在仓库之外。源码和文档使用占位符或独立配置，不写入凭据、账号数据、个人绝对路径或现场业务信息。脱敏范围见 [docs/redaction.md](docs/redaction.md)。

导出读取 Git 暂存区。完成审查后仅暂存准备交付的文件，运行 `python3 scripts/check_export.py` 和 `python3 scripts/package.py`；源码变更后重新暂存、检查、导出。核对最终 ZIP 与暂存 blob 一致，并报告未验证的运行能力。

根 MIT 的范围与目录例外见 [LICENSES.md](LICENSES.md)，第三方署名入口为 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
