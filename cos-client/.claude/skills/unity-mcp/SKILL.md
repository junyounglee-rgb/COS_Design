---
name: unity-mcp
description: Unity MCP 도구 사용법을 참조합니다. Unity Editor와 상호작용할 때 자동으로 로드됩니다.
---

Unity MCP 도구를 사용하여 Unity Editor와 상호작용할 때 이 가이드를 참고하세요.

## 핵심 원칙
- Unity Editor를 CLI(Bash/PowerShell)로 직접 실행하지 마세요. 항상 unity-mcp 도구를 사용하세요.
- `using System.Linq` 대신 `using ZLinq`을 사용하세요 (CK0052 에러 방지).
- Unity_ReadConsole은 Unity 6000.3.x에서 리플렉션 호환 문제로 동작하지 않습니다. Unity_GetConsoleLogs를 사용하세요.

---

## 코드 수정 후 컴파일 검증 워크플로우
`/unity-compile` 스킬을 참조하세요.

요약: ValidateScript → ClearLogs → Refresh → IsCompiling 대기 → GetConsoleLogs 에러 확인

---

## 도구 카테고리별 사용법

### 스크립트 관리

| 도구 | 용도 |
|------|------|
| `Unity_CreateScript` | 새 C# 스크립트 생성 (Path, Contents, ScriptType, Namespace) |
| `Unity_DeleteScript` | 스크립트 삭제 (Uri) |
| `Unity_ManageScript` | 스크립트 CRUD (action: create/read/delete) |
| `Unity_ValidateScript` | 스크립트 검증 (Uri, Level: basic/standard, IncludeDiagnostics) |
| `Unity_ApplyTextEdits` | 정확한 위치 기반 텍스트 편집 (startLine/startCol/endLine/endCol, 1-indexed) |
| `Unity_ScriptApplyEdits` | 구조적 편집 - 메서드/클래스 단위 (replace_method, insert_method, anchor_insert 등) |
| `Unity_FindInFile` | 파일 내 정규식 검색 (Uri, Pattern) |
| `Unity_GetSha` | 파일 SHA256 해시 조회 (편집 충돌 방지용) |

**편집 우선순위**: ScriptApplyEdits (구조적) > ApplyTextEdits (위치 기반) > ManageScript update (전체 덮어쓰기)

### 에디터 제어

| 도구 | 용도 |
|------|------|
| `Unity_ManageEditor` | 에디터 상태 제어 (Play/Pause/Stop/GetState/GetSelection/AddTag/AddLayer 등) |
| `Unity_ManageMenuItem` | 메뉴 아이템 실행/검색 (Action: Execute/List/Exists, MenuPath) |
| `Unity_RunCommand` | C# 코드를 에디터에서 직접 실행 (클래스명 반드시 `CommandScript`, `internal` 접근자) |
| `Unity_GetConsoleLogs` | 콘솔 로그 조회 (types: ["error"/"warning"/"log"]) |
| `Unity_EditorWindow_CaptureScreenshot` | 에디터 스크린샷 캡처 |

### 커스텀 도구 (프로젝트 전용)

| 도구 | 용도 |
|------|------|
| `Unity_Refresh` | Unity 에디터 새로고침 (AssetDatabase.Refresh + 컴파일 트리거) |
| `Unity_ClearLogs` | Unity ConsoleWindow 로그 클리어 |
| `Unity_IsCompiling` | Unity 컴파일 중인지 확인 (isCompiling 반환) |

### GameObject & Scene

| 도구 | 용도 |
|------|------|
| `Unity_ManageGameObject` | GameObject CRUD, 컴포넌트 추가/제거/조회 (action: create/modify/delete/find/get_components 등) |
| `Unity_ManageScene` | 씬 관리 (Action: Create/Load/Save/GetHierarchy/GetActive/GetBuildSettings) |
| `Unity_Camera_Capture` | 특정 카메라 렌더링 캡처 (cameraInstanceID) |

### 에셋 관리

| 도구 | 용도 |
|------|------|
| `Unity_ManageAsset` | 에셋 CRUD/검색/이동/복제 (Action: Import/Create/Modify/Delete/Search/GetInfo 등) |
| `Unity_FindProjectAssets` | 이름 + 시맨틱 에셋 검색 (query) |
| `Unity_ListResources` | 프로젝트 파일 목록 조회 (Pattern, Under, Limit) |
| `Unity_ReadResource` | 리소스 파일 읽기 (Uri, StartLine, LineCount) |
| `Unity_ManageShader` | 셰이더 CRUD (Action: Create/Read/Update/Delete) |

### 패키지 관리

| 도구 | 용도 |
|------|------|
| `Unity_PackageManager_GetData` | 패키지 정보 조회 (packageID, installedOnly) |
| `Unity_PackageManager_ExecuteAction` | 패키지 추가/제거 (operation: Add/Remove/Embed, package, version) |

### 프로파일러

| 도구 | 용도 |
|------|------|
| `Unity_Profiler_GetFrameTopTimeSamplesSummary` | 프레임 상위 시간 샘플 요약 |
| `Unity_Profiler_GetFrameGcAllocationsSummary` | 프레임 GC 할당 요약 |
| `Unity_Profiler_GetSampleTimeSummary` | 샘플 시간 요약 |
| `Unity_Profiler_GetSampleGcAllocationSummary` | 샘플 GC 할당 요약 |
| `Unity_Profiler_GetBottomUpSampleTimeSummary` | Bottom-up 분석 시간 요약 |

프로파일러 도구는 모두 `frameIndex`, `threadName` 파라미터가 필요합니다.

---

## Unity_RunCommand 작성 규칙

```csharp
using UnityEngine;
using UnityEditor;

internal class CommandScript : IRunCommand
{
    public void Execute(ExecutionResult result)
    {
        // 로직 작성
        result.Log("결과 메시지");
        // result.RegisterObjectCreation(obj);  // 생성 시
        // result.RegisterObjectModification(obj);  // 수정 전
        // result.DestroyObject(obj);  // 삭제 시
    }
}
```

**필수 규칙:**
1. 클래스명은 반드시 `CommandScript`
2. 접근자는 반드시 `internal`
3. Top-level statements 사용 금지
4. `result` 객체로 로깅 및 변경 추적
