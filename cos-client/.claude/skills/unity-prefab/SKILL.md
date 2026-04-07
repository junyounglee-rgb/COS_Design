---
name: unity-prefab
description: Read, understand, and edit Unity prefab files (.prefab) using the ubridge CLI. Converts Unity YAML to a compact .ubridge format for AI comprehension (92-96% token reduction). Use when asked to inspect, modify, or restructure prefab hierarchies. Requires `ubridge` CLI (npm i -g --install-links github:yulcat/unity-yaml-bridge).
---

# Unity Prefab Editing

Edit Unity prefab files through the `ubridge` CLI, which converts Unity's verbose YAML into a compact `.ubridge` format.

## Prerequisites

```bash
npm i -g --install-links github:yulcat/unity-yaml-bridge
```
If install fails: `git clone https://github.com/yulcat/unity-yaml-bridge.git && cd unity-yaml-bridge && npm install && npm link`

## Workflow

### Read → Edit → Write

```bash
# 1. Parse (always use --project for GUID resolution + nested prefab expansion)
ubridge parse <file.prefab> --project <unity-root> -o /tmp/edit.ubridge

# 2. Edit the .ubridge file (STRUCTURE and DETAILS sections)
#    When adding new components, write all serialized fields explicitly.
#    ubridge does NOT auto-populate defaults like the Unity Editor.

# 3. Write back (-o can safely overwrite the original)
ubridge write /tmp/edit.ubridge --yaml <file.prefab> -o <file.prefab>
```

## .ubridge Format

Three sections:

```
# ubridge v1 | prefab
--- STRUCTURE          ← GameObject tree
--- DETAILS            ← Component properties
--- REFS               ← fileID map (do not modify, but consult for -> references)
```

### STRUCTURE

```
PlayerUI [PlayerController, Health]
├─ HUD [Canvas]
│  ├─ HealthBar [Image, Slider]
│  └─ ScoreText [TextMeshProUGUI]
├─ Weapon {Sword}                    ← nested prefab (recursively expanded)
│  └─ Blade [MeshRenderer]
└─ + DebugPanel [Text]               ← added in variant
```

| Syntax | Meaning |
|--------|---------|
| `[Comp, ...]` | Components (Transform filtered out) |
| `{PrefabName}` | Nested prefab instance |
| `Comp*` | Overridden in variant |
| `+ GO` / `- GO` | Added / removed in variant |
| `GO#N` | Name collision disambiguation |

### DETAILS

```ini
[PlayerUI/HUD/HealthBar:Image]
m_Sprite = {21300000, abc123def456}
m_Color = (1, 0.3, 0.3, 1)
```

Path format: `Root/Parent/Child:ComponentType`. Only non-default values shown.

### REFS

```
PlayerUI/HUD/HealthBar = 1234567890
PlayerUI/HUD/HealthBar:Image = 9876543210
PlayerUI/HUD/ScoreText:TextMeshProUGUI = 5555555555
```

REFS uses **the same slash path format** as DETAILS headers. Do not modify REFS, but use its keys for `->` references.

## Path References (`->`)

Internal cross-references use `->` with a key from REFS:

```ini
targetGraphic = ->PlayerUI/HUD/HealthBar:Image
attackRoot = ->Weapon/Blade:Transform
targets:
  - ->PlayerUI/HUD/HealthBar
  - ->PlayerUI/HUD/ScoreText
```

**The `->` value must exactly match a REFS key.** DETAILS headers and REFS keys use identical slash paths, so you can derive the correct key from either.

`@` is an alias for `->` (both work identically).

Cross-asset references still use `{fileID, guid}` format. Unresolved `->` references cause an error on write-back.

## Value Syntax

| Type | Format | Example |
|------|--------|---------|
| int, float | literal | `5`, `0.42` |
| bool | `0` / `1` | `1` |
| string | literal | `Hello World` |
| Vector | tuple | `(0.5, 0.5)`, `(1, 2, 3)` |
| Color | `(r, g, b, a)` | `(1, 0.9, 0.3, 1)` |
| Asset ref | `{fileID, guid}` | `{21300000, e197d4e8...}` |
| Internal ref | `->Path:Comp` | `->Root/Child:Image` |
| Null | `null` | `null` |
| Array | `[a, b]` | `[->GO1, ->GO2]` |

### Transform Shorthand

```ini
pos = (10, 20)              # anchoredPosition
size = (200, 50)            # sizeDelta
anchor = (0, 0)-(1, 1)     # anchorMin-anchorMax
pivot = (0.5, 0.5)
scale = (1, 1, 1)
rot = (0, 45, 0)           # euler angles
```

See [references/value-syntax.md](references/value-syntax.md) for AnimationCurve, LayerMask, and complex arrays.

## Variant Prefabs

Variants show only overrides. `*` = overridden component, `+` = added GO, `-` = removed GO.

```
# ubridge v1 | variant | base-guid:abc123...
--- STRUCTURE
Enemy [EnemyAI*, SpriteRenderer*]
└─ + Shield [SpriteRenderer]
--- DETAILS
[Enemy:EnemyAI]
speed = 5.0

[+ Shield:SpriteRenderer]
m_Sprite = {21300000, shield-guid}
```

## Limitations

- Scene files (`.unity`) not yet supported
- Nested prefab internal components must be edited via source prefab
- Sibling GOs with identical names use `#N` disambiguation
