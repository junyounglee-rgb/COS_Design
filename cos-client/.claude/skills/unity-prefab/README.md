# unity-prefab

An AI agent skill for reading and editing Unity prefab files (`.prefab`) through the [`ubridge`](https://github.com/yulcat/unity-yaml-bridge) CLI.

Converts Unity's verbose YAML into a compact `.ubridge` format optimized for AI comprehension — **92-96% token reduction** with lossless round-trip fidelity.

## Install

### Via [skills CLI](https://github.com/vercel-labs/skills) (recommended)

```bash
# Global install (available in all projects)
npx skills add yulcat/unity-prefab -a claude-code -g

# Project-local install (share with team via git)
npx skills add yulcat/unity-prefab -a claude-code
```

Also works with Codex, Cursor, Gemini CLI, and [40+ other agents](https://github.com/vercel-labs/skills#available-agents).

### Manual

```bash
git clone https://github.com/yulcat/unity-prefab ~/.claude/skills/unity-prefab
```

## Dependency

This skill requires the `ubridge` CLI:

```bash
npm i -g --install-links github:yulcat/unity-yaml-bridge
```

The skill instructs the agent to install it automatically if missing.

## What It Does

When you ask an AI agent to inspect or edit a Unity prefab, this skill teaches it to:

1. **Parse** — Convert `.prefab` → `.ubridge` (compact, readable)
2. **Read** — Understand the GameObject hierarchy, components, and properties
3. **Edit** — Modify properties, add/remove GameObjects, rewire references
4. **Write back** — Convert `.ubridge` → `.prefab` (lossless)

### Key Features

- **Nested prefab expansion** — Recursively inlines child hierarchies from nested prefab instances
- **Path references (`->`)** — Human-readable `->Button:Image` instead of opaque `{fileID}` numbers
- **Variant support** — Shows only overrides with `*` markers on modified components
- **MonoBehaviour GUID resolution** — Shows actual C# class names instead of raw GUIDs
- **Name collision handling** — Sibling GOs with same name get `#1`, `#2` suffixes
- **92-96% token reduction** — Makes prefabs feasible for LLM context windows

### Example

A Unity prefab that looks like this in YAML (9,488 bytes):
```yaml
--- !u!1 &8027481463175804169
GameObject:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {fileID: 0}
  ...hundreds of lines...
```

Becomes this in `.ubridge` (698 bytes):
```
--- STRUCTURE
Button [ButtonActivation]
├─ Background9Slice_Image [Image]
└─ Button_Text {SkillName_Text} [TextMeshProUGUI]
--- DETAILS
[Button:ButtonActivation]
activateDisplayText = ->Button_Text:TextMeshProUGUI
```

## Links

- **ubridge CLI**: [yulcat/unity-yaml-bridge](https://github.com/yulcat/unity-yaml-bridge)
- **Format spec**: [docs/FORMAT.md](https://github.com/yulcat/unity-yaml-bridge/blob/master/docs/FORMAT.md)
- **Agent Skills standard**: [agentskills.io](https://agentskills.io)

## License

MIT
