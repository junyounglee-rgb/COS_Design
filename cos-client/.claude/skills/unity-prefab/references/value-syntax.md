# Value Syntax Reference

## Scalar Types

| Unity Type | .ubridge | Example |
|------------|----------|---------|
| int | as-is | `5` |
| float | as-is | `0.42` |
| bool | `0` / `1` | `1` |
| string | as-is | `Hello World` |
| enum | int value | `3` |

## Compound Types

| Unity Type | .ubridge | Example |
|------------|----------|---------|
| Vector2 | `(x, y)` | `(0.5, 0.5)` |
| Vector3 | `(x, y, z)` | `(1, 2, 3)` |
| Vector4 | `(x, y, z, w)` | `(0, 0, 0, 1)` |
| Color | `(r, g, b, a)` | `(1, 0.9, 0.3, 1)` |
| Rect | `(x, y, w, h)` | `(0, 0, 100, 50)` |

## References

| Type | .ubridge | Example |
|------|----------|---------|
| Asset ref | `{fileID, guid, type}` | `{21300000, e197d4e89f9f4274, 2}` |
| Internal ref | `{fileID}` | `{8027481463030904456}` |
| Component ref | `->GOPath:Component` | `->Button_Text:TextMeshProUGUI` |
| Null | `null` | `null` |

### Asset Reference GUIDs

Common fileID values in asset references:
- `21300000` — Sprite (in a texture/atlas)
- `11400000` — ScriptableObject (main asset)
- `2100000` — Material
- `7400000` — AnimationClip

## Transform Shorthand

RectTransform and Transform use compact field names:

```ini
[Button:RectTransform]
pos = (10, 20)              # anchoredPosition
size = (200, 50)            # sizeDelta
anchor = (0, 0)-(1, 1)     # anchorMin-anchorMax
pivot = (0.5, 0.5)         # pivot
scale = (1, 1, 1)          # localScale
```

## Arrays

```ini
items = [{21300000, guid1}, {21300000, guid2}]
names = [Alpha, Bravo, Charlie]
```

## Nested Objects (YAML passthrough)

Complex nested objects that don't fit INI syntax appear as indented YAML:

```ini
m_AnimationCurve:
  m_Curve:
    - time: 0
      value: 1
    - time: 1
      value: 0
```
