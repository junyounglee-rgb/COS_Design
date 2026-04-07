---
name: game-data
description: 게임 데이터(cos-data) 구조와 클라이언트에서의 사용법을 참조합니다. GameData 관련 작업 시 자동으로 로드됩니다.
---

# 게임 데이터 (cos-data) - 클라이언트 가이드

게임 데이터 저장소 관련 상세 내용은 [cos-data/CLAUDE.md](../../../cos-data/CLAUDE.md)를 참조하세요.

이 문서는 cos-client에서 게임 데이터를 사용하는 방법에 대해 설명합니다.

## cos-data 경로

```
../cos-data/  (cos-client 기준 상대 경로)
```

## 클라이언트 코드 경로

| 경로 | 설명 |
|-----|------|
| `Assets/Scripts/GameData/` | 게임 데이터 로더 및 접근 클래스 |
| `Assets/Scripts/GameData/Generated/` | Protobuf에서 생성된 C# 코드 |

## GameData 클래스 사용

게임 데이터는 `GameData.Instance`를 통해 접근합니다.

```csharp
// 스킬 정보 조회
var skillInfo = GameData.Instance.GetSkillInfoData(skillId);

// 쿠키 정보 조회
var cookieInfo = GameData.Instance.GetCookieData(cookieId);

// 상태 효과 정보 조회
var statusEffect = GameData.Instance.GetStatusEffectValueData(effectId);

// 스킬 차지 정보 조회
var chargeData = GameData.Instance.GetSkillChargeData(chargeId);
```

## Protobuf 코드 생성

cos-data에서 `./datasheet` 실행 후, 생성된 Protobuf 파일이 클라이언트에 반영됩니다.

```
cos-data/protobuf/
    ↓ protoc 컴파일
cos-client/Assets/Scripts/GameData/Generated/
```
