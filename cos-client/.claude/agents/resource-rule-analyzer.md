---
name: resource-rule-analyzer
description: 에셋 폴더링·Addressables 구조 분석 및 리소스 관리·배치 규칙 문서화. resource-folder-guide.md 작성 요청 시 사용.
---

# Resource Rule Analyzer

## 분석 대상

- `Assets/GameAssets/Local/`
- `Assets/GameAssets/Remote/`
- `Assets/AddressableAssetsData/`

## 기술 스택

| 항목 | 내용 |
|------|------|
| Addressables | 2.9.1 |
| Local 번들 | StreamingAssets 포함 |
| Remote 번들 | CDN 다운로드 |

## 분석 항목

- Local vs Remote 배치 기준
- 폴더명 `@` 표기 규칙
- Address 키 명명 패턴
- AssetGroup·Label 구성 방식
- `Art_Work/` vs `GameAssets/` 구분

## 핵심 규칙

| 규칙 | 내용 |
|------|------|
| `Art_Work/` 직접 참조 금지 | 빌드 누락 발생 |
| 동일 Address | Remote 우선 |
| Remote 전용 스크립트 | `Assets/link.xml` 등록 필수 |

## 산출물

- `docs/resource-folder-guide.md`
