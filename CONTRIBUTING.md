# 新增和更新条目

本仓库按个人私有集合维护。目录约定见 [布局说明](docs/repository-layout.md)，许可范围见 [LICENSES.md](LICENSES.md)。

## 新增 Skill

使用 `skills/<skill-name>/SKILL.md`。YAML frontmatter 至少包含非空 `name`、`description`，目录名与 `name` 一致。说明能力及其触发条件，把只在某个分支需要的细节放入有明确链接的参考文件。只有确实需要时才加 `scripts/`、`references/`、`assets/`。

`agents/openai.yaml` 是可选的界面和调用策略元数据。导入已有条目时保留原策略；单纯补署名或整理目录不改变其显式/自动调用方式。

带浏览器、进程或 MCP 的能力以 `plugins/<name>/` 为迁移单元，保留 Plugin 内的 `skills/`、运行时和配置。普通 Skill 不需要为了统一外观强行改成 Plugin。

## 导入第三方内容

1. 找到原仓库、原作者、原路径和许可证原文，保存可复核的提交链接。只有已查明时才记录原始安装提交；用于比对的提交单列为 `reference_revision`。
2. 将 `LICENSE`、必要 `NOTICE` 与 Skill 一起保留。`SKILL.md` 中加简短可读来源，并在 `metadata` 中记录上游信息。
3. 用目录内 `PROVENANCE.json` 保存来源分类、许可依据、比较范围和本机修改。保留原文件摘要；后续包装改动追加记录，不覆盖为伪造的“上游原版”。
4. 更新 [第三方来源总表](THIRD_PARTY_NOTICES.md) 和 `catalog.json`。来源暂无法核实的条目保持明确的私人归档标识，不用根 MIT 替代缺失的授权依据。

`skills/grill-me/` 是已核实 MIT 来源的示例：原作属于 Matt Pocock，副本保留本机兼容调整和原调用策略。

个人自建内容需明确自己的许可选择；根许可证当前只覆盖 [LICENSES.md](LICENSES.md) 指定的仓库原创维护材料，不自动给所有旧 Skill 授权。

## 修改已有内容

保留来源和原许可，区分上游内容、本机原有改动与本次整理。需要升级上游时先比较实际差异，再合并个人调整。版本化的 vendor 源码保持锁文件一致；修改这些文件需要同时记录差异与新的核验依据。

运行素材、账号状态、截图、文稿、凭据与业务现场信息留在源码树之外。新能力的真实运行状态由当前验收决定，源码存在和工具列出都不等于平台动作已经通过。

## 本地检查

首次准备验证环境：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/validate_repo.py
```

验证器只读工作树，检查 catalog 已纳入的 Skill、代理元数据、目录、来源与许可、维护文档链接和 vendor 哈希；不会执行已归档 Skill。新建但未登记的 Skill 会列为 unregistered，留给独立审查。导出检查会拒绝暂存区中未登记或缺失的 Skill，避免草稿被意外打包。修改脚本或 MCP 逻辑时，再运行能覆盖该改动的相关检查。

小红书运行代码的现有离线测试入口：

```sh
cd plugins/xiaohongshu
python3 -m unittest discover -s tests -q
```

交付前将审查通过的文件按明确路径暂存，再从仓库根执行：

```sh
git diff --cached --check
python3 scripts/check_export.py
python3 scripts/package.py
```

导出内容来自暂存区，工作树改动需要重新暂存。默认输出在仓库外，附 SHA256SUMS。上传和安装是独立操作，按用户当前请求选择目的地和执行范围。
