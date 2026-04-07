---
name: art-asset-analyzer
description: 캐릭터·배경 에셋 내부 구조 분석 및 아트 에셋 연결 규칙 문서화. art-asset-guide.md 작성 요청 시 사용.
---

# Art Asset Analyzer

## 분석 대상

- `Assets/GameAssets/Remote/CH_Cookie@/` (2~3개 샘플)
- `Assets/GameAssets/Remote/CH_Common/`
- `Assets/GameAssets/Remote/BG_Common/`

## 기술 스택

- URP Material (커스텀 셰이더)
- Spine 애니메이션
- Addressables Remote 번들

## 분석 항목

| 항목 | 내용 |
|------|------|
| 폴더 구조 | Animation·Texture·Material·Mesh·Prefab·FX·Timeline |
| Prefab 계층 | GameObject 내부 계층 구조 |
| Texture·Material | 연결 방식 |
| FX 프리팹 | 참조 방식 |
| 파일명 | prefix 명명 패턴 |

## 산출물

- `docs/art-asset-guide.md`
