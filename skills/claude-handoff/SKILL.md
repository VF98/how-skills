---
name: claude-handoff
description: Hand the current conversation off to a fresh background agent that picks up the work immediately.
metadata:
  legacy-argument-hint: What will the next session be used for?
  upstream-author: Matt Pocock
  upstream-repository: https://github.com/mattpocock/skills
  upstream-path: skills/in-progress/claude-handoff
  upstream-reference: 5beb35b040e3de97e54fa9e386d7e42d15c295c2
  provenance: PROVENANCE.json
license: MIT
---

> 来源：[Matt Pocock / skills](https://github.com/mattpocock/skills/tree/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/in-progress/claude-handoff) · [MIT](LICENSE)。本机衍生副本与修改记录见 [PROVENANCE.json](PROVENANCE.json)。

Write a handoff summary of the current conversation so a fresh agent can continue the work. Instead of saving it, launch a background agent seeded with the summary as its prompt: `claude --bg --name "<descriptive name>" "<handoff summary>"`. It starts in the current working directory and returns immediately; the user manages it with `claude agents`.

Always pass `-n`/`--name` with a descriptive name (e.g. `--name "Fix login bug"`); it sets the display name shown in the job list, session picker, and terminal title.

Include a "suggested skills" section in the summary, naming which skills the next agent should call the Skill tool for.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information, since the summary becomes the agent's prompt.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the summary accordingly.
