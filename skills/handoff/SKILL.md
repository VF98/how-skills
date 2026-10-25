---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
metadata:
  legacy-argument-hint: What will the next session be used for?
  upstream-author: Matt Pocock
  upstream-repository: https://github.com/mattpocock/skills
  upstream-path: skills/productivity/handoff
  upstream-reference: 5beb35b040e3de97e54fa9e386d7e42d15c295c2
  provenance: PROVENANCE.json
license: MIT
---

> 来源：[Matt Pocock / skills](https://github.com/mattpocock/skills/tree/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/productivity/handoff) · [MIT](LICENSE)。本机衍生副本与修改记录见 [PROVENANCE.json](PROVENANCE.json)。

Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save to the temporary directory of the user's OS - not the current workspace.

Include a "suggested skills" section in the document, naming which skills the next agent should call the Skill tool for.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
