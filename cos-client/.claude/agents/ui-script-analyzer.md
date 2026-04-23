---
name: ui-script-analyzer
description: UI 스크립트 패턴·코드-프리팹 연결 방식 분석 및 신규 UI 스크립트 작성 가이드 문서화. ui-script-guide.md 작성 요청 시 사용.
---

# UI Script Analyzer

## 분석 대상

- `Assets/Scripts/UI/` (PanelManager, PopupManager)
- `Assets/Scripts/UIComponent/` (LoopList, UITween)
- `Assets/Scripts/OutGame/UI/`
- `Assets/Scripts/InGame/UI/`

## 기술 스택

- MonoBehaviour 컴포넌트 패턴
- UniTask (비동기 UI)
- DOTween · FMOD · Odin Inspector

## 분석 항목

| 항목 | 내용 |
|------|------|
| Panel/Popup 흐름 | 열기·닫기 흐름 |
| 베이스 클래스 | 상속 구조 |
| SerializeField | 바인딩 패턴 |
| 이벤트·콜백 | 연결 방식 |
| UIComponent | 재사용 규칙 |

## 산출물

- `docs/ui-script-guide.md`
