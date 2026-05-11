---
name: protocol
description: 'Launch a named expert protocol. Usage: /protocol <name> <task>. Run /protocol with no args to list available protocols.'
---

# Protocol — Expert Team Router

## Purpose

Route to a named protocol (expert panel). Each protocol is a fixed roster of domain experts that work on whatever task the user provides.

## Instructions

### Parse Input

The user invokes: `/protocol <name> <task>`

- If no arguments: list available protocols (see below) and stop.
- If only a name with no task: ask "What should Protocol <Name> work on?"
- If name + task: dispatch to the matching protocol skill.

### Available Protocols

| Protocol  | Skill            | Roster                                                                                                                                                                            |
| --------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **brains** | `protocol-brains` | 2 Database, 2 TypeScript architects, 1 Legacy Migration, 1 React, 1 Test, 1 Monorepo, 2 Multiagent workflow, 1 Orchestration  |
| **pinky** | `protocol-pinky` | 2 React architects, 1 TS architect, 1 State/Data, 1 MUI, 1 UX/a11y, 1 Contracts, 1 Test, 1 i18n, 1 Security, 1 Performance, 1 Business Impact, 1 Backend Contract, 1 Monorepo, 1 Tailwind, 1 UI Component Library  |

### Dispatch

Invoke the matching skill using:

```
Skill: protocol-<name>, args: "<task>"
```

If the protocol name is not recognized, say:

> "Unknown protocol: `<name>`. Available protocols: brains, pinky"

## Output (when listing)

```
## Available Protocols

| Protocol | Experts |
|----------|---------|
| **brains** | 2 Database, 2 TS architects, 1 Legacy Migration, 1 React, 1 Test, 1 Monorepo, 2 Multiagent workflow, 1 Orchestration |
| **pinky** | 2 React architects, 1 TS architect, 1 State/Data, 1 MUI, 1 UX/a11y, 1 Contracts, 1 Test, 1 i18n, 1 Security, 1 Performance, 1 Business Impact, 1 Backend Contract, 1 Monorepo, 1 Tailwind, 1 UI Component Library |

Usage: /protocol <name> <task>
```
