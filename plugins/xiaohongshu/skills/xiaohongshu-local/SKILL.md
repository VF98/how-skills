---
name: xiaohongshu-local
description: 在独立本地浏览器中创作和修改小红书图文、上传授权配图、保存并重开同一条草稿。搜索或最终发布使用同包的可选上游组件；本 MCP 只处理文稿和草稿。
license: Apache-2.0
---

# 小红书文稿与草稿

优先调用 `xiaohongshu-local` 提供的 `xhs_*` MCP 工具。工具未加载时，从本插件根目录运行 `python3 scripts/run.py --help`，使用同源 CLI。仅云端执行环境无法访问本机浏览器。

## 环境

先调用 `xhs_doctor`。分发入口默认使用 `isolated_headless`，运行数据位于用户的独立数据目录，源码包不带账号或验收记录。需要登录时调用 `xhs_isolated_status(capture_login=true)`，展示返回的官方登录截图，让用户本人扫码确认，再检查状态。

遇到登录、风控、权限拒绝、超时或状态冲突时保留已有状态并说明。保持独立 profile；不复制日常浏览器 Cookie，不回退到日常 Chrome，也不通过改变网络或指纹绕过限制。

## 创作、上传与修改

1. 修改已有稿件时，先用 `xhs_platform_draft_list` 找到文稿 ID，再用 `xhs_local_manuscript_get` 读取当前版本。新稿用 `xhs_local_manuscript_create`，素材限于用户授权的本地图片。
2. 用 `xhs_local_manuscript_update` 沿用文稿 ID 和 `expected_revision`。版本冲突时读取新版本；本地预览明确标注为本地文稿。
3. 用户已授权该篇内容和素材上传、草稿保存时，调用 `xhs_platform_draft_sync`。首次上传图片，后续修改沿用同一个原生草稿 ID。
4. 仅当 `platform_saved` 和 `reopened_verified` 都为真时报告保存成功。用 `xhs_platform_draft_reopen` 重开核对，保留同一原生 ID。
5. 结果未明时先 `xhs_platform_draft_inspect`；`xhs_platform_draft_reconcile` 仅在内容版本和图片数量完全匹配时继续保存，避免重复上传和写入。

标题、正文和标签文字支持同条修改。现有图片替换、排序、平台话题实体绑定尚未实现；完整浏览器重启恢复需在目标机器验证。详见 [本地组件说明](../../docs/local-backend.md)。

## 搜索与发布

此本地 MCP 的消费者搜索在隔离模式下停用，也没有最终发布工具。需要搜索、读取笔记或发布时，读取 [可选上游组件](../../docs/upstream.md) 和同包 `xiaohongshu-search-publish` Skill，检查独立上游服务是否已配置。缺少对应工具时报告缺口。

本地草稿属于当前浏览器 profile；可选上游发布会以文稿内容重新创建笔记，不能把它声称为直接发布现有原生草稿。最终发布需要针对具体账号、内容和素材的用户授权。
