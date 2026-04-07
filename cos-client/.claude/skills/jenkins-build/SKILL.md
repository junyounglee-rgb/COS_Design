---
name: jenkins-build
description: 젠킨스 빌드 파이프라인 구조와 빌드 플로우를 참조합니다. 빌드 관련 작업 시 자동으로 로드됩니다.
---

# 젠킨스 빌드 파이프라인

COS Unity 클라이언트 빌드를 위한 Python 기반 빌드 파이프라인입니다.
- 경로: `../cos-client-build/` (cos-client 기준 상대 경로)

## 빌드 타입

파이프라인은 두 가지 빌드 명령어를 지원합니다:

| 빌드 타입 | 설명 |
|----------|------|
| `run_addressable_build` | 어드레서블 빌드 (리소스 번들만) - cos-resource에 푸시 후 포탈 업로드 |
| `run_client_build` | 클라이언트 빌드 (전체 앱) - AOS/IOS 빌드 후 포탈 및 Firebase 업로드 |

## 주요 모듈

### 메인 파이프라인
| 모듈 | 설명 |
|-----|------|
| `Pipeline.py` | 메인 진입점, 인자 파싱 및 워크플로우 조정 |
| `global_var.py` | 빌드 파라미터 중앙 상태 관리 |
| `const.py` | 상수 정의 |

### 빌드 실행
| 모듈 | 설명 |
|-----|------|
| `client_builder.py` | Unity 배치 모드 실행 (어드레서블/클라이언트 빌드) |
| `ipa_builder.py` | iOS XCode archive 및 export |
| `AppSealing.py` | Android 앱 난독화/보호 |

### Git 및 업로드
| 모듈 | 설명 |
|-----|------|
| `git_updater.py` | Git 작업 (clone, checkout, commit, push, 브랜치 관리) |
| `upload_addressable.py` | 어드레서블 번들 포탈 업로드 |
| `dev_portal_uploader.py` | 빌드 결과물 포탈 업로드 |
| `firebase_symbol_uploader.py` | Firebase Crashlytics 심볼 업로드 |

### 유틸리티
| 모듈 | 설명 |
|-----|------|
| `version_checker.py` | Unity ProjectSettings에서 버전 추출 |
| `slack_notification.py` | 빌드 상태 Slack 알림 |
| `cleaner.py` | 빌드 정리 |
| `util.py` | 공통 유틸리티 함수 |

## 빌드 플로우

### 어드레서블 빌드 (`run_addressable_build`)
```
Git Clone → Unity 빌드 → cos-resource 푸시 → 포탈 업로드
```

### 클라이언트 빌드 (`run_client_build`)
```
Git Clone → 버전/리비전 결정 → Unity 빌드 → 플랫폼 후처리 → 포탈 업로드
```

## Unity 빌드 메서드

파이프라인은 Unity를 배치 모드로 호출합니다:
- `BuildScript.PrepareBuildClientFromJenkins`: 빌드 전 준비
- `BuildScript.BuildClientFromJenkins`: 전체 클라이언트 빌드
- `BuildScript.BuildPatchFromJenkins`: 어드레서블 전용 빌드

## 셸 스크립트

| 스크립트 | 설명 |
|---------|------|
| `start_jenkins_agent.sh` | Jenkins 에이전트 시작 |
| `install_daemons.sh` | Jenkins daemon 설치 |
| `prepare_local_repo.sh` | 로컬 저장소 준비 |
| `install_mobileprovision.sh` | iOS 프로비저닝 프로파일 설치 |
