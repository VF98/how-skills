---
name: lark-ops
description: Operate Lark/Feishu through the installed lark-cli for documents, Drive, Wiki, IM messages and groups, Base, Sheets, calendars, mail, tasks, approvals, meetings, contacts, and authentication. Use whenever the user asks to read, search, create, edit, send, or manage a Feishu/Lark resource, or provides a Feishu/Lark/Doubao resource URL or token.
---

# Lark/Feishu operations

Use `lark-cli` as the only integration layer. Reuse its embedded, version-matched skills instead of copying command documentation into this skill.

## Route the request

1. Run `lark-cli skills list` and select every domain needed by the request.
2. Read the shared rules with `lark-cli skills read lark-shared`.
3. Read each selected domain skill with `lark-cli skills read <skill-name>` and follow it completely. Read referenced files with the same command, for example `lark-cli skills read lark-doc references/<file>.md`.
4. For unsupported operations, read `lark-openapi-explorer` and use raw API calls only as the last resort.

Typical routes include `lark-doc` for document content, `lark-drive` for files and folders, `lark-wiki` for knowledge spaces, `lark-im` for messages and chats, `lark-base` for multidimensional tables, `lark-sheets` for spreadsheets, `lark-calendar` for events, and `lark-task` for tasks.

## Execute safely

- Prefer shortcut commands, then typed API commands, then raw API calls.
- Inspect unfamiliar syntax with `lark-cli <domain> --help` and `lark-cli schema <service.resource.method>`; do not guess arguments.
- Use the configured profile and effective identity unless the user specifies another. Check with `lark-cli whoami` when identity affects ownership or visibility.
- For outbound Feishu IM messages or replies, default to bot identity (`--as bot`). Use user identity only when the user explicitly requests it or the operation is user-only. If bot permissions, membership, visibility, or availability prevent delivery, report the constraint and ask before switching identity; never silently fall back to `--as user` or start user authorization.
- Treat the user's explicit write request as authorization for that exact operation. Use `--dry-run` before ambiguous, bulk, destructive, or irreversible writes.
- If exit code 10 reports `confirmation_required`, show the action and key parameters and wait for explicit approval. Append `--yes` only after approval.
- Determine success from exit code 0 or `ok: true`, never from a missing or zero `code` field.
- Return concise results with useful names, IDs, and URLs; do not dump full API envelopes unless requested.

## Protect credentials

- Never print app secrets, access tokens, refresh tokens, or device codes.
- On authentication or scope errors, follow the current `lark-shared` split-flow and QR-code instructions.
- Keep file inputs and outputs relative to the command working directory, as required by `lark-cli`.
