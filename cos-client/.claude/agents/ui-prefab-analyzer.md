---
name: ui-prefab-analyzer
description: UI 프리팹 구조·컴포넌트 구성·명명 규칙 분석 및 신규 UI 프리팹 제작 가이드 작성. ui-prefab-guide.md 작성 요청 시 사용.
---

# UI Prefab Analyzer

## 분석 대상

- `Assets/GameAssets/Local/UI/UI_Prefab/`
- `Assets/GameAssets/Remote/UI/`
- `Assets/GameAssets/Remote/UI_Asset/`

## 기술 스택

| 항목 | 내용 |
|------|------|
| Unity | 6000.3.9f1 · URP |
| TextMesh Pro | - |
| Addressables | 2.9.1 |
| DOTween | - |

## 분석 항목

| 항목 | 내용 |
|------|------|
| 프리팹 계층 | Canvas → Panel → 컴포넌트 |
| 컴포넌트 패턴 | Image, TMP_Text, Button, ScrollRect |
| 명명 규칙 | 파일명·GameObject명 prefix/suffix |
| 애니메이션 | DOTween vs Animator |
| 배치 기준 | Local/Remote 구분 |

## 산출물

- `docs/ui-prefab-guide.md`
