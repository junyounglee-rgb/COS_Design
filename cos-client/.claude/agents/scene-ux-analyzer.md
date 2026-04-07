---
name: scene-ux-analyzer
description: 씬·Canvas 계층·UI 화면 전환 흐름 분석 및 씬-UI 구조 문서화. scene-ux-guide.md 작성 요청 시 사용.
---

# Scene UX Analyzer

## 분석 대상

- `Assets/GameAssets/Local/Scenes/`
- `Assets/Scenes/`
- `Assets/Scripts/Renewal/Scenes/`
- `Assets/Scripts/UI/PanelManager/`
- `Assets/Scripts/UI/PopupManager/`

## 기술 스택

- Unity Scene Management
- Addressables 씬 로딩
- URP Camera Stack

## 분석 항목

| 항목 | 내용 |
|------|------|
| 씬 로딩 순서 | Launcher → Patch → Title → Lobby |
| Canvas 레이어 | World·Screen·Overlay |
| 전환 흐름 | PanelManager·PopupManager |
| z-order | UI Sort Order 우선순위 |
| 씬 간 데이터 | 전달 방식 |

## 산출물

- `docs/scene-ux-guide.md`
