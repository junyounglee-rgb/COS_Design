---
name: unity-compile
description: 코드 수정 후 Unity 컴파일 검증 워크플로우입니다. 코드 수정/작성 완료 시 자동으로 로드됩니다.
---

코드를 수정한 후 Unity 컴파일 검증을 수행해주세요.

## 검증 순서

### 1단계: 콘솔 클리어 + Unity Refresh
1. `mcp__unity-mcp__Unity_ClearLogs`로 콘솔 로그를 클리어하세요.
2. `mcp__unity-mcp__Unity_Refresh`로 Unity 에디터를 새로고침하세요 (AssetDatabase.Refresh + 컴파일 트리거).

### 2단계: 컴파일 완료 대기
`mcp__unity-mcp__Unity_IsCompiling`으로 컴파일 상태를 확인하세요.
- `isCompiling: true`이면 잠시 후 다시 실행하여 `false`가 될 때까지 대기하세요.
- `isCompiling: false`이면 컴파일이 완료된 것이므로 다음 단계로 진행하세요.
- 도메인 리로드 중 MCP 연결이 끊길 수 있습니다. 에러 시 재시도하세요.

### 3단계: 콘솔 에러 확인 (Unity_GetConsoleLogs)
컴파일 완료 확인 후 `mcp__unity-mcp__Unity_GetConsoleLogs`로 에러를 확인하세요:
- types: ["error"]
- 에러가 있으면 수정 후 다시 1단계부터 반복하세요.
- MCP 플러그인 자체 에러(Unity.AI.MCP, ReadConsole 등)는 무시하세요.

## 주의사항
- Unity Editor를 CLI로 직접 실행하는 Bash/PowerShell 명령은 절대 사용하지 마세요.
- 항상 unity-mcp 도구를 통해서만 Unity와 상호작용하세요.
- `using System.Linq` 대신 `using ZLinq`을 사용하세요 (CK0052 에러 방지).
