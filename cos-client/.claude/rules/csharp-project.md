# cos-client 프로젝트 규칙

## Null 안전 (CK Analyzer CK0011~CK0015)

| 상황 | 잘못 | 올바름 |
|------|------|--------|
| string ?? | `str ?? "default"` | `str.Ref() ?? "default"` |
| ?.chain → string ?? | `obj?.Name ?? ""` | `obj?.Name.Ref() ?? ""` |
| UnityObject ?. | `Instance?.Method()` | `Instance.RefObj()?.Method()` |
| RefObj() 후 | `obj.RefObj().Do()` | `obj.RefObj()?.Do()` |

- RefObj() 결과를 로컬 변수에 캐싱 금지 (non-nullable 추론 → ?. 에러)
- string .Ref()에 `using COS;` 필요
- **코드 수정 후 `??`와 `?.` 포함된 모든 라인 재검증**

## LINQ (CK0052)
`using System.Linq` 금지 → `using ZLinq` 사용

## 비동기 패턴 (UniTask)
| 잘못 | 올바름 |
|------|--------|
| `async void Method()` | `async UniTaskVoid Method()` |
| `SomeUniTask();` | `SomeUniTask().Forget();` |

## 프로젝트 전용 API
| 금지 | 대체 | 이유 |
|------|------|------|
| `Debug.Log/Warning/Error` | `PNLog.Log/Warning/Error` | ENABLE_LOG 조건부 컴파일 |
| `EditorUtility.DisplayDialog` | `EditorUtil.DisplayDialog` | CK Analyzer 에러 |
| `Substring(n)` | Range 연산자 `str[n..]` | CK Analyzer 에러 |
| Unity CLI 직접 실행 | unity-mcp 도구 사용 | MCP 통한 상호작용 필수 |
