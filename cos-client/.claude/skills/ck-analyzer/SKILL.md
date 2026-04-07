---
name: ck-analyzer
description: CK Roslyn Analyzer 규칙을 참조합니다. 코드 작성/수정/리뷰 시 자동으로 로드됩니다.
---

# CK Roslyn Analyzer 규칙

이 프로젝트는 CK Roslyn Analyzer를 사용합니다. 코드 작성/수정 시 아래 규칙을 반드시 준수하세요.
설정 파일: `Assets/Plugins/Editor/Analyzers/config.CK.Analyzer.additionalfile`

## 금지 API (ExternalObsoleteAnalyzer - CK0051/CK0052)

`OnlyAssemblyCSharp: true`이면 Assembly-CSharp에서만 CK0051, 아니면 모든 어셈블리에서 CK0052.

### MethodInfos - 금지 메서드

| 금지 API | 대체 API | 비고 |
|----------|----------|------|
| `UnityEngine.Debug.Log/LogWarning/LogError/LogException` | `PNLog.Log/LogWarning/LogError/LogException` | Assembly-CSharp 전용 |
| `UnityEngine.Object.DestroyImmediate` | `UnityObjectExtensions.DestroyImmediateSafe` | 모든 어셈블리 |
| `UnityEditor.EditorUtility.DisplayDialog` | `EditorUtil.DisplayDialog` | `COS.EditorUtil` 내부 제외 |
| `UnityEditor.EditorUtility.DisplayDialogComplex` | `EditorUtil.DisplayDialogComplex` | `COS.EditorUtil` 내부 제외 |
| `UnityEditor.AssetDatabase.StartAssetEditing` | `AssetDatabase.AssetEditingScope` | 모든 어셈블리 |
| `UnityEditor.AssetDatabase.StopAssetEditing` | `AssetDatabase.AssetEditingScope` | 모든 어셈블리 |
| `Material.EnableKeyword/DisableKeyword` | `ShaderHelper` | `ShaderHelper` 내부 제외 |
| `Shader.EnableKeyword/DisableKeyword` | `ShaderHelper` | `ShaderHelper` 내부 제외 |
| `TMPro.TMP_Text.SetText` | `TString` | 특정 클래스/경로 제외 |
| `GameData.Instance.DT{X}.TryGetValue` | `GameData.Instance.TryGet{X}` | GameData 내부 |
| `GameData.Instance.DT{X}.ContainsKey` | `GameData.Instance.Contains{X}` | GameData 내부 |

### TypeInfos - 금지 타입

| 금지 타입 | 대체 타입 |
|-----------|----------|
| `System.Threading.Tasks.Task` | `Cysharp.Threading.Tasks.UniTask` |

### SetterInfos - 금지 Setter

| 금지 Setter | 대체 API |
|-------------|----------|
| `TMPro.TMP_Text.text =` (setter) | `TMPro.TMP_Text.SetText()` |

### NamespaceInfos - 금지 네임스페이스

| 금지 네임스페이스 | 대체 | 비고 |
|-------------------|------|------|
| `using System.Linq` | `using ZLinq` | **필수** |
| `using Java` | - | 사용 금지 |
| `using Castle` | - | 사용 금지 |
| `using Boo.Lang` | - | 사용 금지 |
| `using UnityScript` | - | 사용 금지 |
| `using System.Diagnostics.Debug` | - | 사용 금지 |
| `using FMOD.Studio` | - | `Assets/Scripts/Sound/` 경로 제외, Assembly-CSharp 전용 |

## Null 처리 (RefNullAnalyzer - CK0011~CK0015)

### UnityEngine.Object 타입
`??`, `?.`, `??=`, `is null` 직접 사용 금지. 반드시 `.RefObj()` 먼저 호출.

```csharp
// 잘못된 방식 (CK0011~CK0014)
Transform t = target ?? defaultTarget;
target?.DoSomething();
target ??= fallback;
if (target is null) {}

// 올바른 방식
Transform t = target.RefObj() ?? defaultTarget;
target.RefObj()?.DoSomething();
if (target.RefObj() == null) {}
```

**CK0015**: `RefObj()` 호출 후 반드시 `?.`로 이어져야 함
```csharp
// 잘못된 방식
obj.RefObj().Method();
// 올바른 방식
obj.RefObj()?.Method();
```

**RefObj() 결과를 로컬 변수에 캐싱 금지** - non-nullable로 추론되어 `?.` 에러
```csharp
// 잘못된 방식
var mgr = PopupManager.Instance.RefObj();
mgr?.Show();  // 컴파일 에러

// 올바른 방식 (인라인 체이닝만)
PopupManager.Instance.RefObj()?.Show();
```

### System.String 타입
`??`, `?.` 직접 사용 금지. `.Ref()` 먼저 호출 (`using COS;` 필요).
단, `??=` (CK0013)은 string에서 제외됨.

```csharp
// 잘못된 방식
string result = errorMessage ?? string.Empty;
string name = user?.Name ?? "unknown";

// 올바른 방식
string result = errorMessage.Ref() ?? string.Empty;
string name = user?.Name.Ref() ?? "unknown";
```

## Unity 직렬화 (SerializableAnalyzer - CK0021~CK0024)

- **CK0021**: `[SerializeField]`에 사용하는 enum은 `[SerializableEnum]` 필요
  - 제외 네임스페이스: UnityEngine, UnityEditor, DG.Tweening, Devsisters, Town.Web.Protocols 등
- **CK0022**: `[SerializableEnum]` 멤버는 명시적 숫자 값 필요
- **CK0023**: 부모 클래스와 중복된 직렬화 필드 금지
- **CK0024**: `[SerializableEnum]`에서 중복 숫자 값 금지

## 비동기 패턴 (CK0031, CK0091~CK0093)

- **CK0031**: `async void` 금지 → `async UniTask` 또는 `async UniTaskVoid`
- **CK0091**: UniTask 반환값 무시 시 `.Forget()` 필수
- **CK0092**: `UniTask.WaitUntil/WaitWhile`에서 `static` 람다 사용
- **CK0093**: static 람다 내 Instance 호출 금지

```csharp
// 잘못된 방식
async void OnClick() { }
SomeUniTaskMethod();
await UniTask.WaitUntil(() => isReady);

// 올바른 방식
async UniTaskVoid OnClick() { }
SomeUniTaskMethod().Forget();
await UniTask.WaitUntil(static () => isReady);
```

## 기타 규칙

- **CK0001/CK0002**: enum switch문 모든 case 처리 필수
- **CK0041/CK0042**: `[RequiredModifiers]` 지정 타입은 static/readonly 필수
- **CK0053**: Unity 메시지(Awake, Start, Update 등) 직접 호출 금지
- **CK0054**: `UnityEditor` 네임스페이스 사용 시 `#if UNITY_EDITOR` 필수
- **CK0055**: `[RestrictedTo]` 어트리뷰트로 호출자 제한된 메서드
- **CK0061**: 존재 확인만 할 때 `TryGetValue` 대신 `ContainsKey`
- **CK0062**: `out var _` 대신 `out _`
- **CK0081**: `[RequiredInitialize]` 필드는 반드시 초기화
- **UNT0021**: Unity 메시지 메서드는 `protected` 접근 제한자
