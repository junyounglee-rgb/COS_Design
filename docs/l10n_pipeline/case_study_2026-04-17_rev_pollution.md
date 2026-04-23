# 사례 분석: Lokalise rev 누적 오염 사건 (해결 완료)

> 발생일: 2026-04-17 17:40 KST
> 종료일: 2026-04-18 05:24 KST
> 총 소요: 11시간 44분
> 출처: Slack `#translation` 관련 채널 스레드 (총 256건) + cos-data git log (2026-04-17 17:00 ~ 2026-04-18 05:30)
> 상태: **이슈 해결 완료**

---

## 읽기 전: 용어 해설

> 실무자가 아닌 관리자도 이해할 수 있도록 핵심 용어를 먼저 정리합니다.

### 1. 번역 파이프라인 구성 요소

| 용어 | 한 줄 정의 | 역할 |
|------|-----------|------|
| **translations.xlsx** | 기획자가 **한국어 원문**을 입력하는 Excel 파일 | 모든 언어의 출발점. 원칙적으로 한국어는 오직 이 파일에서만 수정되어야 함. |
| **Lokalise (로컬라이즈)** | 번역팀이 웹에서 한국어를 보고 영/일/중/태/인니 번역을 입력하는 유료 SaaS | 구글 시트 같은 건데 번역 전용. 번역팀은 이 웹 페이지에서만 작업. |
| **dictionary (.pb 파일)** | 서버가 실제 게임에 배포할 때 읽는 **번역 캐시 바이너리** | Excel → datasheet → dictionary(.pb) → 서버가 로드 → 플레이어에게 번역 노출. 중간 캐시 역할. |
| **datasheet (도구)** | Excel → dictionary(.pb) 변환 CLI 도구 | 기획자/PM이 Windows/Mac에서 수동 실행. 이번 사건에서 **재컴파일**이 일어남. |
| **Fork (포크)** | Git 작업용 GUI 툴 이름 (SourceTree 계열) | 기획자가 터미널 대신 사용. 내부에서 Git Bash 호출. |

### 2. 사건을 이해하는 핵심 개념 (비유 포함)

**rev (레비전, revision) = Lokalise 내부 버전 번호**
- 한국어 원문이 수정될 때마다 rev 1 → rev 2 → rev 3 ... 이렇게 누적됨 (이력 보관).
- 최신 rev만 게임에 나가야 정상. 옛날 rev도 저장소 안에 그대로 남아 있음.
- **문제**: 옛 rev가 실수로 배포에 섞이면 → **이미 수정된 옛 오타가 게임에 다시 등장**.
- 비유: 회사 주소록이 5번 개정됐는데 옛 주소록들이 캐비닛에 다 쌓여 있고, 직원이 실수로 3년 전 주소록을 꺼내 쓰면 엉뚱한 곳으로 택배가 가는 상황.

**publish / unpublished = Lokalise 게시 상태**
- **publish** = "이 번역을 게임에 반영해도 된다"고 승인된 상태. publish 되어야 실제 배포에 포함.
- **unpublished** = 번역 작업은 했는데 **게시 해제** 상태 → 게임에 빈칸 또는 한국어로 노출됨.
- 이번 사건의 "21개 publish 누락" = 기획자는 등록했다고 생각하지만 Lokalise에 제대로 게시되지 않은 21개 키.
- 이번 사건의 "unpublished 14건" = 실수로 게시 해제된 14건 → 플레이어 관점에선 **버그로 보임**.
- 비유: 택배 포장은 다 끝났는데 "출고" 버튼을 안 눌러 창고에 쌓여만 있는 상태.

**대표키 병합 (Differentiate keys by file 옵션)**
- Lokalise 설정: "한국어 원문이 같은 키들은 하나로 묶어서 관리"하는 옵션.
- 예: `mail_template^10.title = "쿠키 달성!"`, `mail_template^20.title = "쿠키 달성!"` → Lokalise가 "같은 번역이지" 판단 → **^20은 별도 등록되지 않음**.
- **설계 의도**: 같은 한국어를 중복 번역하는 번역팀 비용 절감.
- **이번 사건의 문제**: 기획자는 ^20도 등록됐다고 생각 → Lokalise는 ^10만 앎 → ^20 위치에 대응되는 영어 번역이 **게임에서 빈칸**.
- 비유: 사내 문서 자동분류기가 제목이 같은 문서를 "중복"으로 판단해 하나만 보관 → 실제로는 내용이 다른 두 번째 문서가 사라짐.

**libc 에러 (`panic: no console`)**
- 기술 설명: datasheet 도구가 **Windows + Fork** 조합에서 콘솔 핸들을 못 찾고 강제 종료되는 환경 제약 (modernc.org/libc 라이브러리 한정).
- 실무 의미: "Windows 기획자는 Fork의 번역키 추출 버튼을 누를 수 없다" — 즉 한쪽 OS에서만 작동하는 도구.
- 이번 사건에서의 역할: **도화선**. 17:40 소준영 PM이 추출을 시도했다가 이 에러가 뜨면서 대응이 시작됨.

### 3. 이번 사건의 원인 구조 (3줄 요약)

```
① Lokalise 웹 수동 수정 (편법)
    ↓
② Excel / Lokalise / dictionary → 세 곳의 한국어 원문이 제각각 달라짐 (3중 불일치)
    ↓
③ 옛 rev들이 최신 배포에 섞여 나감 → 21개 publish 누락 + 6종 오타 복귀 + 빌드 실패
```

- **①의 비유**: 회사의 공식 주소록(Excel)을 바꾸지 않고, 급하다는 이유로 배송팀 개인 노트(Lokalise)에만 새 주소를 써둔 상황.
- **②의 비유**: 총무팀·HR·배송팀이 각자 다른 주소록을 들고 있어서 한 사람의 주소가 3곳에 3개 버전으로 존재.
- **③의 비유**: 택배 기사가 옛 주소록을 들고 가서 엉뚱한 집에 배송.

---

## 사건 개요

| 항목 | 내용 |
|------|------|
| **트리거** | 17:40 "04/17 로컬라이즈 번역키 등록 작업" 공지 후 Fork 번역키 추출 실패 |
| **최초 에러** | `panic: no console` (Windows + Fork 조합 libc 에러) |
| **핵심 원인** | Lokalise 웹 수동 수정 → Excel과 dictionary 상태 불일치 → rev 누적 |
| **영향 범위** | 21개 publish 누락 + 6종 오타 + 4개 등록 실패 + unpublished 14건 |
| **주요 참여자** | 소준영(요청 PM) / 이경우(PM) / 이상유(dev) / 고지희(기획) / 마재의(dev) / 김려강(기획) / 김윤희(기획) |
| **대응 결과** | datasheet 도구에 rev 중복제거 기능 추가 + Excel 단일 원문 원칙 확립 |
| **반복성** | **이번이 처음이 아님** — COS 프로젝트 내에서만 2026년 2~4월(약 2.5개월) 사이 동일 근본원인 사건이 **5건 반복** 발생 (상세: "유사 사례" 섹션) |

---

## 전체 타임라인 (6 Phase)

> 이 섹션의 전문 용어(rev, publish, 대표키 병합, libc 에러 등)는 앞의 **"읽기 전: 용어 해설"** 섹션에 비유 포함 설명이 있습니다.

### Phase 1 — 번역키 추출 환경 문제 (17:40 ~ 21:08, 3시간 28분)

**Slack 이벤트:**

| 시각 | 발생 |
|------|------|
| 17:40:12 | 소준영 PM, 로컬라이즈 번역키 등록 공지 |
| 17:42:24 | 소준영, Fork 추출 시도 → `panic: no console` (Windows libc 에러) |
| 18:02:02 | 지희, Mac에서 시도 → `Cannot read translations.pb: no such file` |
| 20:17:29 | 김려강, Mail 4개 키 로컬라이즈 미등록 확인 (`mail_template^19/20.message/title`) |
| 20:22:01 | 김윤희, `EventInfos^10080.name` 오타 수정 요청 ("배틀 부스트" → "배틀 보너스") |
| 20:27:15 | 상유, **대표키 병합 규칙 확인**: `^20.title`이 `^10.title`의 대표키로 묶여서 **신규 등록 안 됨** (두 키의 한국어가 같기 때문) — ^20 위치에 대응되는 영어 번역이 게임에서 빈칸으로 나올 상태 |
| 21:06:41 | 소준영, "Windows에서는 Fork로 추출 안 됨" 확인 — **도화선이었던 libc 에러**가 Windows+Fork 조합 한정 환경 제약임이 확정됨 |
| 21:07:27 | 상유, "터미널에서 직접 실행하면 되는 문제" 판단 → Fork 대응 스크립트 수정 착수 |

**Git 커밋 활동 (이경우):**

```
20:19  test: deploy merged datasheet binary for keyword_test verification
20:22  test: deploy merged datasheet binary for release_test/vng_test verification
20:26  test: inject FK violation on keyword_test  ← FK violation 주입 테스트
20:45  test (x2)
20:53  binary update (1차)
20:59  binary update (2차) ← datasheet-linux-amd64 (0 → 8MB), linux-arm64 (0 → 6.5MB) 신규 추가
```

> **핵심**: 경우님이 Linux 바이너리를 cos-data에 **신규 추가**. 이전엔 macOS/Windows만 존재. Fork/Windows 환경 우회를 위해 서버 실행 경로 확보.

### Phase 2 — 21개 publish 누락 확인 (21:23 ~ 23:02, 1시간 39분)

**Git 커밋 활동:**

```
21:23  shell script 수정 (x3 — main/release_helsinki3/release_istanbul)
21:41  fork lokalise 스크립트 수정 (x3 cherry-pick)
         .fork/extract_translations.sh  -50줄 삭제
21:49  소준영 main-branch에서 번역키 추출 성공
22:14  지희 Sync lokalise all keys (1차) ef2762599
22:18  지희 Sync lokalise all keys (2차) 5792519b4
```

**Slack 이벤트:**

| 시각 | 발생 |
|------|------|
| 22:58:00 | 경우, **21개 publish 누락 키 리스트 공유** (mode_types 14 + ui_strings 3 + event_infos 3 + product 1) — 즉 **21개 번역이 "포장은 끝났는데 출고 버튼을 안 누른 상태"**로 게임에 안 반영됨 |
| 23:02:50 | 상유, "로컬라이즈와 dictionary 싱크 안 맞는 부분 강제 동기화 예정" — 번역 웹 도구(Lokalise)와 서버 캐시(dictionary)가 다른 내용을 들고 있어 수동 맞춤 작업 돌입 |

**누락된 21개 키 전체 목록:**

```
Product.first_buy_bonuses^2.popup_description~rev2
Modes.mode_types^MODE_TYPE_BATTLE_ROYAL.name
Modes.mode_types^MODE_TYPE_BATTLE_ROYALE_TEAM.name
Modes.mode_types^MODE_TYPE_BOUNTY.name
Modes.mode_types^MODE_TYPE_CASTLE_BREAK.name
Modes.mode_types^MODE_TYPE_COIN_RUSH.name
Modes.mode_types^MODE_TYPE_DEATH_MATCH.name
Modes.mode_types^MODE_TYPE_DEV_TOWN.name
Modes.mode_types^MODE_TYPE_DROP_THE_BEAT.name
Modes.mode_types^MODE_TYPE_ESCORT.name
Modes.mode_types^MODE_TYPE_GNOME_BATTLE.name
Modes.mode_types^MODE_TYPE_JELLY_RACE.name
Modes.mode_types^MODE_TYPE_ROUND.name
Modes.mode_types^MODE_TYPE_TRAINING.name
Modes.mode_types^MODE_TYPE_TUTORIAL.name
UIStrings.ui_strings^UI_Event_OpenBattleBox_Description.text~rev2
UIStrings.ui_strings^UI_Setting_Menu_FPS_Alarm_Desc.text~rev2
UIStrings.ui_strings^UI_Setting_Menu_Graphic_Alarm_Desc.text~rev2
EventInfos.event_infos^60020.name
EventInfos.event_infos^60070.name
EventInfos.event_infos^60090.name
```

- **~rev2 접미사 4개**: product.popup_description / ui_strings 3건 → **옛 버전이 최신 배포에 섞였다는 직접 증거** (rev 누적 오염의 스모킹건)
- **Modes.mode_types 14개**: 배틀로얄/바운티/코인러시 등 **기본 게임모드 이름 전체**가 unpublished 상태 — 번역은 존재하지만 "게시" 처리 누락 → 게임 화면에 모드 이름이 빈칸 또는 한국어로 노출

### Phase 3 — 원인 규명: rev 누적 오염 발견 (23:13 ~ 23:38, 25분)

**Slack 이벤트:**

| 시각 | 발생 |
|------|------|
| 23:13 | 상유, dictionary-Lokalise 강제 동기화 완료 — **서버 캐시(dictionary)와 번역 웹(Lokalise)의 내용이 다를 때 둘 중 한쪽 값으로 강제로 맞추는 작업** (PM이 손으로 진행) |
| 23:15~16 | 상유, **`번역키 강제 업데이트` 커밋** (65f15f035, 6f973a663) |
|         | → attendance_events/dialog_groups/mail/quests/ui_strings 등 14개 pb 파일 수정 (**xlsx 없음** = 한국어 원문은 그대로인데 서버용 바이너리만 직접 고친 상태 → 다음 빌드에서 원문이 다시 덮어씌울 위험) |
| 23:25:56 | **지희 충격 발견: "옛날 오타가 불러와지다니..."** |
|         | → `못했어~`로 3/26에 수정했는데 `못했서~`가 다시 등장 (옛 rev 복귀 현상) |
| 23:27:25 | 상유, **"혹시 그거 로컬라이즈에서 고치셨나요?"** |
| 23:27:34 | **지희: "네 로컬라이즈에서 수동으로 고쳤어여"** |
| 23:27:38 | **상유: "그럼 안됩니다... 무조건 엑셀에서 고쳐야 해요"** — 원칙 확립 (원문 수정 경로를 **단 하나(Excel)**로 통일) |
| 23:28:35 | 상유: "언제나 스트링을 바꿀 때는 엑셀을 바꾼다가 되어야 해요" |
| 23:30:15 | 지희: "각 기획 담당자가 사혼의 구슬처럼 하는 작업이라..." (**기획자 소환 비용** = 오타 하나 고치려 해당 담당 기획자를 찾아 직접 Excel을 열게 해야 하는 부담 → 그래서 편법 유혹 지속) |
| 23:37~38 | 상유, **`번역키 강제동기화` 커밋** (3d69e3c59, 4d609652e) |
|          | → items/maps/product/quests/skill_infos/translations pb 재정렬 (서버 캐시 재정비) |

**Git 증거 — 3/26 "못했어~" 수정의 부재:**

```
dialog_groups.xlsx 3월 25~28일 커밋 전체:
  03-25 13:12  [김율희] 최종 다이얼로그 반영
  03-25 13:23  [김율희] 잘못들어간 대사 수정
  03-25 18:07  [김율희] 퀘스트와 대화 등장 간격 조절 반영
  03-26 11:17  [김율희] 다이얼로그 마들렌 1번 조건 수정
  03-27 22:04  [김율희] 마들렌 줄바꿈 수정
```

→ 지희가 말한 "3/26 수정" **Excel 커밋은 없음** (즉 공식 주소록은 안 바뀜)
→ 즉 Excel은 `못했서~` 그대로였고, Lokalise 웹에서만 `못했어~`로 수정됨 (배송팀 개인노트만 바꾼 상황)
→ **다음 datasheet 실행 시 Excel의 `못했서~`가 재업로드 → rev3로 다시 생성** (공식 주소록을 다시 배포 → 개인노트 수정분이 무효가 되고 옛 오타가 부활)

### Phase 4 — 개선안 논의 (23:43 ~ 23:48, 5분)

> **주요 용어**
> - **LLM 봇 / 오타 검출 봇**: AI가 한국어 문장을 자동 검사해 오타 후보를 알려주는 자동화 도구 제안.
> - **CI (Continuous Integration)**: 코드/데이터가 저장소에 올라올 때마다 자동으로 검증·빌드를 돌리는 서버 자동화 시스템.
> - **false positive (노이즈)**: 실제 오타가 아닌데 봇이 오타라고 잘못 경고하는 경우 → 너무 많으면 결국 사람이 무시하게 됨.

| 시각 | 발언자 | 내용 |
|------|--------|------|
| 23:43 | 경우 | "로컬라이즈 올리기 전에 검수하면 좋을 것 같아요" |
| 23:43 | 지희 | "키가 600개씩 뽑힐 때는 사람 검수 많이 빡세긴 할텐데..." |
| 23:43 | 마재의 | **"엑셀기반 수정 ← 이건 무조건 해야합니다"** (원문 수정 경로 단일화 필요) |
| 23:44 | 마재의 | "로컬라이즈만 수정하고 엑셀에 수정 안 한 사람 있으면 혼내야 하고" |
| 23:45 | 마재의 | "귀찮은건: 1.엑셀수정 2.datasheet 3.업로드 4.확인 5.sync — 스텝 2~3개 추가" (현재 구조에서 Excel 수정 원칙을 지키려면 **기획자가 5단계를 모두 손으로** 해야 함) |
| 23:47 | 마재의 | **"오타는 LLM 한번 돌릴만 할지도? CSV로 뽑히는거면"** (AI 오타 검출기 제안) |
| 23:47 | 상유 | **"데이터에 CI로 LLM 오타 잡는 봇 같은거 하나 만들어봄직하다"** (자동화 서버에 AI 맞춤법 봇 탑재 제안) |
| 23:48 | 김려강 | "맞춤법검사기가 봇으로 오는건가용" |
| 23:48 | 상유 | "그런 느낌이죠" |
| 23:48 | 마재의 | "근데 엄청 노이지할거에요" (**노이지 = false positive 우려** — 봇이 잘못 경고하는 건수가 많아 담당자가 알림을 무시하게 되는 현상) |

### Phase 5 — 오염 데이터 수정 실행 (23:53 ~ 00:20, 27분)

**Slack 이벤트:**

| 시각 | 발생 |
|------|------|
| 23:53 | 지희, "21개 키 + 라이크 이슈 키만 우선 업로드?" |
| 23:56 | 경우, **"엑셀은 보관하셔야할거가타요"** (편법 수정 금지 — **Excel을 안 고치고 Lokalise만 고치면 이번 사건이 또 반복**됨) |
| 23:56 | 경우, "아니면 어드민툴에서 unpublished로 두던가" (→ 임시로 **"게시 해제"** 상태로 두면 배포에서 빠지므로 게임 노출은 막을 수 있다는 우회안) |
| 00:03 | **지희, 오타 6종 리스팅 완료** |
| 00:04 | 마재의, "지희님이 직접 수정해서 올리면 안되나요?" (**기획자 소환 비용** 회피: 다른 담당자 부르지 말고 지희님이 Excel 직접 수정하자) |
| 00:05 | 마재의, "prefix로 파일 대충 맞출수있는데요: dialog_groups/items/ui_strings.xlsx" (**키 이름 앞부분(prefix)으로 어느 Excel 파일을 수정해야 하는지 찾을 수 있다**는 팁 — 예: `DialogGroups.xxx` 오타 → `dialog_groups.xlsx` 열면 됨) |
| 00:06 | 상유, "cos-data에 datasheet.exe 있죠? 수정하시고 한번 딸깍 누르시면" (**발견자 = 수정자** 원칙 — Excel만 고치고 datasheet.exe 실행 한 번이면 끝) |
| 00:11 | **상유 `오탈자 수정` 커밋 (dd325965f)** |
| 00:11 | 상유, "main 업로드했어요" |
| 00:19 | 상유, "**그게 이미 로컬라이즈에 번역되어 있기 때문에** 오타 수정 키들만 없어서" (→ 해석: 영/일/중 번역은 이미 완료돼 있어 새로 번역 요청은 불필요. **한국어 원문만 고치면 자동으로 올바른 외국어로 연결**됨) |
| 00:20 | 지희, "나머지는 때려서 로컬라이즈 웹에 임시 번역 해둘게요" (긴급 임시조치 — **구조상 허용된 영문 이하 번역 직수정 범위**임) |

**Git 증거 — `dd325965f 오탈자 수정` 커밋 (상유, 00:11):**

```
excel/dialog_groups.xlsx       809488  → 809735  bytes
excel/items.xlsx               326058  → 325683  bytes
excel/ui_strings.xlsx          170425  → 169644  bytes
protobuf/dialog_groups.pb     1065264  → 1065264 bytes
protobuf/items.pb              265520  → 265504  bytes
protobuf/translations.pb      1037680  → 1037664 bytes
protobuf/ui_strings.pb         267408  → 267392  bytes
```

> items/ui_strings xlsx는 오히려 **줄어듬** → **불필요한 옛 rev가 정리되면서 파일이 작아짐**을 시사 (쓰레기 데이터 청소 효과)

**지희가 리스팅한 오타 6종 (00:03):**

```
1. DialogGroups.dialog_groups^11051600001.dialogs^10.dialog_text
   "나 때는 이런 도시는 상상도 못했서~"  →  "못했어~"

2. DialogGroups.dialog_groups^500002.dialogs^10.dialog_text
   "이 퀘스트는 테스트용 퀘스트야~"  →  삭제 또는 격리

3. Items.items^130020201.info
   "반죽 탄 자국을 모니 남몰래 서핑 연습..."
   →  "반죽 탄 자국을 보니 남몰래..."

4. UIStrings.ui_strings^Pre_Language_Popup_ChineseTraditional.text
   "繁體"  →  "繁體中文"

5. UIStrings.ui_strings^Setting_Language_ChineseTraditional.text
   "繁體"  →  "繁體中文"

6. UIStrings.ui_strings^Setting_Language_Indonesian.text
   "Indonésia"  →  "Indonesia"
```

### Phase 6 — 새벽 청소 작업 + 후속 정리 (00:42 ~ 05:24, 4시간 42분)

> **이 단계 한 줄 요약**: "오염된 옛 rev를 전부 청소하기 위해 **02:57 새벽에 datasheet 도구 자체를 새 기능으로 다시 빌드**하고, 7개 언어 엑셀을 모두 재정리한 대공사 시간대."

**Slack 이벤트:**

| 시각 | 발생 |
|------|------|
| 00:42 | 지희, "영문 데이터는 로컬라이즈 웹 수정해도 괜찮죠?" |
| 00:42 | 상유, **"네 국문만 원문으로 취급해요"** — 규칙 확정 (한국어만 Excel 전용, **영/일/중/태/인니는 Lokalise 웹 수정 허용**) |
| 01:11 | 지희, 스킬 설명 툴팁 잘림 건의 (딕셔너리 UX — **번역문이 길어 게임 UI에서 잘리는 현상** 개선 요청) |
| 01:12 | 상유, "뷰어도 들어가서 보는 메뉴를 살려두겠습니다" — 후속 약속 |
| 05:09 | 경우, `Pre_Language_Popup_Indonesian.text` "Indonésia(é)" 재확인 (**인니어에 프랑스어 악센트 é가 섞인 오타**를 재검토 — VNG 법인 작업 흔적) |
| 05:22 | 지희, "VNG 작업 기준 저 값으로 되어 있어서 따르는 게 맞아요" (→ **VNG(베트남 법인)가 이미 그 값으로 운영 중**이라 우리 쪽을 VNG에 맞추기로 결정) |
| 05:24 | 경우, "넵넵" — 스레드 종결 |

**Git 증거 — 이경우의 새벽 rev 청소 대작업:**

```
02:57  [I1] ui_string translations.pb rev 중복제거 (a1cfe43c8)
         datasheet                 46932270 → 46938158 bytes  ← 도구 재컴파일!
         datasheet-linux-amd64      8007864 →  8009744 bytes
         datasheet-linux-arm64      6565396 →  6564500 bytes
         datasheet.exe              8146944 →  8144896 bytes
         protobuf/translations.pb    974464 →   974416 bytes

03:38  [I1] ui_string translations.pb rev 중복제거 (1ccb1dc52)
03:38  [I1] ui_string translations.pb rev 중복제거 (931b7f1b9)
03:39  [I1] ui_string translations.pb rev 중복제거 (ce1bb5df2)
03:39  [I1] ui_string translations.pb rev 중복제거 (fd85fcfc9)

03:48~05:03  Sync lokalise specific keys (5회) ← 경우
              translations_XX.xlsx 7개 언어 반복 sync

04:17  translations_lang.pb uistring rev 제거 (244388a71)
         excel/translations_en.xlsx      321219 → 370253 bytes  (+15%)
         excel/translations_in.xlsx      315540 → 365565 bytes  (+16%)
         excel/translations_ja.xlsx      346534 → 409153 bytes  (+18%)
         excel/translations_ko.xlsx      342063 → 396327 bytes  (+16%)
         excel/translations_th.xlsx      373539 → 494316 bytes  (+32%)  ← 대폭 증가
         excel/translations_vi.xlsx      376150 → 436900 bytes  (+16%)
         excel/translations_zh-hant.xlsx 273908 → 304859 bytes  (+11%)
```

> **`datasheet` 바이너리가 02:57에 재컴파일됨** = **Excel→서버 변환 도구 소스코드를 새벽 3시에 수정해 새로 빌드**했다는 의미. 평소엔 도구는 그대로 두고 데이터만 수정하는데, **도구 자체가 옛 rev를 걸러내지 못해 도구를 뜯어고친 것** → 사태의 심각성을 단적으로 증명.
>
> **태국어 xlsx가 32% 증가** = rev 청소를 하면 파일이 줄어드는 게 상식인데 왜 늘었나? → **그동안 중복 rev에 묻혀 보이지 않던 정상 번역들이 청소 후 제자리를 찾아 다시 노출**된 결과. 즉 "이번 청소로 숨어 있던 데이터까지 같이 복구됐다"는 증거.

---

## 이번 사건이 드러낸 구조적 문제 6가지

> 이 섹션의 전문 용어(rev, publish, 대표키, libc 등)는 문서 상단의 **"읽기 전: 용어 해설"**에 비유 포함 설명이 있습니다.

### 1. Windows + Fork 환경 번역키 추출 실패 (**신규**)

```
panic: no console
modernc.org/libc/libc_windows.go:362
```

| 항목 | 내용 |
|------|------|
| 증상 | Fork에서 번역키 추출 버튼 클릭 시 libc panic |
| 원인 | `modernc.org/libc` Windows GUI 환경 stdin/stdout 미연결 |
| 임시 대응 | 터미널에서 직접 `datasheet.exe` 실행 |
| 근본 대응 | `fork lokalise 스크립트 수정` 커밋 (21:41, 50줄 삭제) |
| 영향 | Windows 사용 PM은 Fork 이용 불가 → 터미널 학습 필수 |

### 2. 같은 국문 → 대표키 자동 병합 (**신규**)

```
Mail.mail_template^19.message  =  "동일 국문 A"  ← 대표키
Mail.mail_template^19.title    =  "동일 국문 B"  ← 대표키
Mail.mail_template^20.message  =  "동일 국문 A"  ← ^19.message에 병합, 등록 안 됨
Mail.mail_template^20.title    =  "동일 국문 B"  ← ^19.title에 병합, 등록 안 됨
```

| 항목 | 내용 |
|------|------|
| 원인 | Lokalise "Differentiate keys by file" 해제 정책 |
| 발견자 | 김려강 (20:17) |
| 부작용 | 같은 국문을 쓰는 2개 이상 키 중 나중 키는 등록 자체가 안 됨 |
| 우회 | 지금 운영은 해당 키를 로컬라이즈 웹에 수동 등록 |
| 근본 문제 | 키-값 1:N 관계인데 Lokalise는 값 기반 병합 |

### 3. Lokalise 웹 수동 수정 → rev 누적 오염 (**핵심**)

```
[정상 흐름]
  Excel (ko="못했서~") → datasheet → Lokalise rev1="못했서~"
  (공식 주소록 → 변환 도구 → 웹 도구에 초판 등록)

[편법 수정 시점]
  Lokalise 웹 수동수정 → rev1 그대로 두고 Publish만 "못했어~"
  Excel은 여전히 "못했서~"
  (공식 주소록은 그대로, 배송팀 개인노트만 수정한 상태)

[다음 datasheet 실행 시]
  Excel (ko="못했서~") → datasheet → Lokalise rev2="못했서~" (새 rev!)
  → rev1(unpublished), rev2(신규 unpublished), publish는 편법수정 값
  → 진실의 원천 완전 상실
  (공식 주소록 재배포로 개인노트 덮어쓰기 → 옛 오타 부활)
```

**이번 사건에서 실제로 발생한 rev 누적:**

- `dialog_groups^11051600001.dialogs^10.dialog_text` (지희가 3/26 웹수정, 4/17 재오염)
- `Product.first_buy_bonuses^2.popup_description~rev2`
- `UIStrings.ui_strings^UI_Event_OpenBattleBox_Description.text~rev2`
- `UIStrings.ui_strings^UI_Setting_Menu_FPS_Alarm_Desc.text~rev2`
- `UIStrings.ui_strings^UI_Setting_Menu_Graphic_Alarm_Desc.text~rev2`

### 4. dictionary ↔ Lokalise 싱크 불일치 (**신규**)

| 시스템 | 역할 | 상태 |
|--------|------|------|
| **Excel** | 원문 저장소 | ko 컬럼 = 진실의 원천 (이론상) |
| **dictionary (DB)** | 서버용 번역 캐시 | pb 파일로 배포 |
| **Lokalise** | 번역 UI + rev 관리 | 웹 수정 가능 = 오염 유입점 |

- 상유 23:02: "로컬라이즈랑 dictionary랑 서로 싱크 안맞는 부분 한번 강제로 동기화할 예정"
- 상유 23:15, 23:16, 23:37, 23:38: `번역키 강제 업데이트/동기화` 커밋 4회 — pb 파일만 수정
- 즉 **3개 시스템이 서로 다른 진실을 가지는 상태**가 실제로 발생

### 5. 테스트 스트링 방치

```
DialogGroups.dialog_groups^500002.dialogs^10.dialog_text
  = "이 퀘스트는 테스트용 퀘스트야~"
```

- 게임에서 참조하지 않는 데이터도 번역 파이프라인 포함
- 기획자가 개발 중 넣은 텍스트 미정리
- 번역팀이 번역 대상인지 모르고 그대로 번역 수행

### 6. VNG 외부 법인 데이터 간섭

```
UIStrings.ui_strings^Setting_Language_Indonesian.text = "Indonésia"
```

- VNG 빌드에서 작업한 값이 메인 Lokalise 프로젝트에 그대로 남음
- 지희 05:22: "VNG 작업 기준 저 값으로 되어 있어서 따르는 게 맞을 것 같아요"
- 한글 빌드에서는 노출 안 되지만 데이터 정합성 관점에서 오해 유발

---

## 스레드 + 커밋으로 확인된 실제 투입 리소스

| 역할 | 투입 시간 | 주요 활동 |
|------|----------|----------|
| **이경우 (PM)** | 약 **9시간** (20:19 ~ 05:24) | binary update, Fork 스크립트 수정, test 커밋 5회, rev 중복제거 도구 개발, Sync lokalise 5회 |
| **이상유 (dev)** | 약 **5시간** (20:23 ~ 01:12) | dictionary-Lokalise 동기화, 오탈자 수정, PR 검토 |
| **고지희 (기획)** | 약 **8시간** (17:42 ~ 05:24) | 데이터 최신화 재시도, 오타 리스팅, 수동 Sync 4회, 오탈자 재검증 |
| **마재의 (dev)** | 약 **20분** (23:43 ~ 00:05) | 원칙 확립, 개선안 제안 (LLM 봇) |
| **김려강 (기획)** | 약 **10분** (20:17 ~ 20:28) | 누락 4개 키 발견 |
| **김윤희 (기획)** | 약 **5분** (20:22) | 별도 오타 1건 요청 |
| **소준영 (요청 PM)** | 약 **3시간** (17:40 ~ 21:06) | Fork 추출 시도, 공지 |

**총 팀 투입: 약 25시간 분량의 실시간 대응**

---

## 스레드에서 **확정된** 운영 규칙 (4건)

| 규칙 | 확정 시각 | 확정자 | 발언 |
|------|----------|--------|------|
| 엑셀이 유일한 원문 수정 경로 | 23:27 | 이상유 | "무조건 엑셀에서 고쳐야 해요" |
| 영문 이하 번역은 Lokalise 웹 수정 OK | 00:42 | 이상유 | "국문만 원문으로 취급해요" |
| 로컬라이즈 unpublished 키는 보관 | 23:56 | 이경우 | "엑셀은 보관하셔야할거가타요" |
| 오타 발견 시 발견자 직접 수정 가능 | 00:06 | 이상유 | "cos-data에 datasheet.exe 있죠? 딸깍 실행" |

## 스레드에서 **미결정** 개선 과제 (5건)

| 제안 | 제안자 | 상태 | 비고 |
|------|--------|------|------|
| CI에 LLM 오타 검출 봇 | 이상유, 마재의 | 아이디어 | "엄청 노이지할거에요" 우려 |
| 맞춤법 검사기 봇 | 김려강 | 아이디어 | 위 봇과 동일 개념 |
| Lokalise 업로드 전 사전 검수 | 이경우 | 아이디어 | 600개/회 부담 |
| Fork 번역키 추출 Windows 지원 | 이상유 | 조사 중 | `fork lokalise 스크립트 수정` 커밋 후 일부 대응 |
| 뷰어 툴팁 길이 확인 메뉴 | 이상유 | 구현 예정 | 딕셔너리 UX 개선 |

## 이번 사건으로 **실제 구현된** 개선 (2건)

| 개선 | 실행자 | 커밋 | 비고 |
|------|--------|------|------|
| **datasheet 도구에 rev 중복제거 기능 추가** | 이경우 | `a1cfe43c8` (02:57) | 바이너리 4종 재컴파일 |
| **Linux 바이너리 cos-data에 신규 추가** | 이경우 | `68c0fcd72` (20:59) | Windows 우회 환경 확보 |

---

## Google Sheet 방식에서 이 사건이 어떻게 차단되는가

### 직접 비교 표

| 이번 발견 문제 | 현재 구조 (Lokalise) | Google Sheet 구조 |
|--------------|-------------------|------------------|
| Windows + Fork 추출 실패 | datasheet.exe 로컬 환경 의존 | CI가 Linux 서버에서 자동 실행 |
| 대표키 자동 병합 | "Differentiate keys by file" 해제 정책 | str_id 기반 → 국문 같아도 독립 |
| Lokalise 웹 수동수정 → rev 누적 | 양방향 수정 경로 | 수정 경로 단일 (Sheet만) |
| dictionary ↔ Lokalise 불일치 | 3개 시스템 간 동기화 필요 | Sheet 단일 소스, dictionary 개념 없음 |
| generated pb files differ 충돌 | pb 커밋 정책 때문 | pb 커밋 제거 (CI 자동 생성) |
| 21개 publish 누락 unpublished 관리 | Lokalise 내부 상태 개념 | `tag=hold/done/new/re` 명시 관리 |
| 600개 검수 부담 | 수동 검수 | diff 기반 변경 분량만 검수 |
| 기획자 소환 비용 (25시간 총투입) | 편법 유혹 지속 | 발견자 즉시 수정 가능 |
| 테스트 스트링 방치 | 번역 파이프라인 포함 | `tag=hold`로 격리 |
| VNG 외부 법인 간섭 | 단일 Lokalise 프로젝트 공유 | VNG 전용 Sheet 또는 필터 컬럼 |

### 전환 시 예방되는 작업 시간

- 오늘 투입된 **25시간** → Google Sheet 기준으로 재산정:
  - 오타 발견 → 발견자 Sheet 직접 수정: **약 5분**
  - CI가 자동으로 ko CSV 생성 + 배포: **5분**
  - 번역팀 알림 수신 → 번역 입력: **10분/키**
  - 21개 publish 누락 상황 자체가 **구조적으로 발생 불가**

---

## 유사 사례 — 이번이 처음이 아니다 (COS 전용)

> Slack 검색 결과, **COS 프로젝트 내에서만** 2026년 2월 초부터 4월 중순까지 약 2.5개월 사이 동일 근본 원인에서 비롯된 사건이 **5건 반복** 발생.
> "개인 실수"가 아니라 **구조적 결함의 반복 발현**임을 확인.

### 시간순 사례 요약

| 날짜 | 채널 | 사건 요약 (관리자용 쉬운 설명 포함) | 근본 원인 |
|------|------|-----------------------------------|----------|
| 2026-02-05 | `#cos_game_design` | `Modes.modes^1303.name` 번역키 충돌로 **datasheet 빌드 강제 종료 (panic) → 빌드 차단**<br>• translations.xlsx: "드롭 더 비트 (스페카드 난사)"<br>• modes.xlsx: "드롭 더 비트"<br>→ 같은 키의 한국어가 두 엑셀에서 다름 → 변환 도구가 **"어느 게 진짜?" 판단 불가** → 강제 종료 | **Excel 내 이중 소스 불일치** (같은 키의 원문이 두 파일에 따로 존재) |
| 2026-02-20 | `#cos_local` | VNG(베트남/인니) 번역본 업로드 시 기존 키에 언어만 추가되지 않고 **새로운 키로 중복 등록**<br>→ 전체 삭제 후 재업로드<br>로컬라이즈 PM(지혜): "해당 옵션이 체크되어 있을 거라는 생각을 미처 못했네요" | **대표키 병합 옵션(Differentiate keys) 체크 실수** — PM도 매번 수동 확인해야 함 |
| 2026-03-07 | `#cos_dev_help` | `SkillInfos.skill_infos^30023000.skill_description`에 두 가지 값이 동시 존재<br>기획자가 키를 `30022000 → 5152000`으로 변경했으나 Lokalise는 이전 키를 모름<br>개발자 경우: "저번에 binary 이상할 때 돌린 게 남아있었나봐요"<br>→ **과거 임시 조치의 잔여물**이 최신 파일에 섞여 있음 | **git 커밋 누락 + 이력 꼬임 + Excel/Lokalise 불일치** |
| 2026-03-11 | `#cos_local` | 애플스토어 검수 긴급 대응 중, 임시 영어 번역이 필요한 키 **303건의 태깅이 누락**되어 번역이 반영되지 않음. 패키지 상품 키 포함.<br>로컬라이즈 PM(조경주): "지금 COS 프로젝트 로컬라이즈에 일부 번역문이 업로드 안되는 **로컬라이즈 버그**가 발견되어서 수정중입니다" | **Lokalise 수동 태깅 한계 + Lokalise 도구 자체 버그** |
| 2026-04-17 | `#cos_outgame` | **본 사건: 11시간 44분 대응, 팀 전체 25시간 투입, datasheet 재컴파일, 21개 publish 누락 + 6종 오타 + unpublished 14건** | **rev 누적 + 세 시스템 3중 충돌 복합** |

### 근본 원인 패턴 매트릭스 (COS 내 5건)

```
                                      │ 02.05 │ 02.20 │ 03.07 │ 03.11 │ 04.17 │
──────────────────────────────────────┼───────┼───────┼───────┼───────┼───────┤
대표키 병합 설정 실수                   │       │   ✅  │       │       │   ✅  │
(Differentiate keys 체크 해제 놓침)     │       │       │       │       │       │
──────────────────────────────────────┼───────┼───────┼───────┼───────┼───────┤
Excel / Lokalise / dictionary           │   ✅  │       │   ✅  │       │   ✅  │
세 시스템 불일치                         │       │       │       │       │       │
(같은 키가 여러 곳에서 다른 값을 가짐)    │       │       │       │       │       │
──────────────────────────────────────┼───────┼───────┼───────┼───────┼───────┤
Lokalise 게시 상태(publish) 누락        │       │       │       │   ✅  │   ✅  │
──────────────────────────────────────┼───────┼───────┼───────┼───────┼───────┤
git 커밋 누락/꼬임 →                    │       │       │   ✅  │       │   ✅  │
바이너리·엑셀 잔여물 오염                │       │       │       │       │       │
──────────────────────────────────────┼───────┼───────┼───────┼───────┼───────┤
PM/숙련자조차 실수                       │       │   ✅  │       │   ✅  │   ✅  │
(수동 작업의 구조적 한계 증거)            │       │       │       │       │       │
```

### 이 패턴에서 도출되는 결론

1. **개인 숙련도 문제가 아니라 구조적 결함이다**
   - 02-20 지혜(로컬라이즈 PM), 03-11 조경주(PM), 04-17 이경우(PM) — **PM 포지션의 숙련자들조차 반복 실수**
   - "잘 확인하면 되는 일"이라는 접근은 2.5개월간 5회 반복에도 해결되지 못함

2. **발생 주기가 급속도로 짧아지고 있다**
   - 2월: 2건 (2주 간격)
   - 3월: 2건 (4일 간격)
   - 4월: 25시간 대응 1건
   - → **데이터 규모와 복잡도 증가에 따라 구조적 한계 노출이 가속**

3. **5건 모두 수동 우회로만 봉합되었다**
   - 02-05: "기획에서 datasheet 돌려서 diff 파일 같이 커밋" (기획자 추가 작업)
   - 02-20: "올려주신 키들 일괄 삭제 후 재업로드" (로컬라이즈 PM 추가 작업)
   - 03-07: "binary 이상할 때 돌린 게 남아있었나봐요" (개발자 수동 디버깅)
   - 03-11: 303건 태깅 재작업 + MLML 자동 번역 보강
   - 04-17: **팀 25시간 투입 + datasheet 도구 재컴파일**
   - → 근본 해결 없이 임시방편만 누적 → 다음 사건의 복잡도 심화

4. **수동 작업 기반 파이프라인의 한계**
   - 모든 사례의 공통점: **사람이 매번 옵션·태그·순서를 확인해야 함**
   - 체크박스 하나, 태그 하나만 놓쳐도 즉시 장애 발생
   - 스케일이 커질수록 누락 확률 선형 증가

### Google Sheet 전환 시 각 사례 차단 방식

| 유사 사례 원인 | 현재 구조에서의 한계 | Google Sheet 전환 시 차단 메커니즘 |
|---------------|-------------------|--------------------------------|
| 대표키 병합 설정 실수 | "Differentiate keys" 옵션을 매번 수동 확인 | **업로드 개념 자체가 소멸** — 기획자가 Sheet에 직접 입력하므로 옵션 선택 자체가 없음 |
| 세 시스템 불일치 | Excel/Lokalise/dictionary 간 동기화 필요 | **Sheet 단일 소스** — dictionary 개념 자체가 없음 (CI가 매번 Sheet에서 생성) |
| publish 상태 누락 | Lokalise 내부 상태를 수동 관리 | **tag 컬럼으로 명시적 관리** (new / re / done / hold) |
| 바이너리 잔여물 오염 | 로컬 binary 실행으로 잔여물 발생 | CI가 매번 새로 생성 → 잔여물 개념 자체가 없음 |
| 숙련자의 반복 실수 | 모든 단계에 수동 확인 필요 | **수동 작업 자체가 0** (기획자는 Sheet 입력만, 나머지 CI 자동) |

---

## 교훈

### 1. 이 사건은 "관리자 실수"가 아니다

- 25시간 투입은 개인 숙련도 문제가 아니라 **구조적 결함의 반복**
- 3/26 지희의 Lokalise 웹 수정은 "편법"이 아니라 **기획자 소환 비용 회피의 합리적 선택**

### 2. "엑셀 수정 안 한 사람 혼내기"는 해결책이 아니다

- 마재의 "혼내야 한다"는 발언은 규율 의존 접근
- 편법 경로가 매력적인 이상 계속 사용됨
- **편법 경로 자체를 구조적으로 차단**해야 근본 해결

### 3. LLM 오타 검증 CI는 **증상 대응일 뿐**

- 오타가 생기는 이유는 Lokalise 웹 수동수정 때문
- LLM 봇은 rev 누적 자체는 막지 못함
- 근본 원인인 양방향 수정 구조를 그대로 두면 의미 반감

### 4. Google Sheet 전환의 **실증적 근거**

- 이론/예상이 아니라 **실제 25시간 손실 + datasheet 도구 긴급 개발**
- datasheet 도구에 rev 중복제거 기능이 **새벽 3시에 추가**되어야 할 만큼 심각
- 이런 사건이 다음 번에도 반복될 가능성이 매우 높음

### 5. 단일 소스 원칙의 중요성

- Excel / dictionary / Lokalise 3개 시스템이 각자 다른 진실을 가지면 **반드시 꼬인다**
- Google Sheet는 진실의 원천을 하나로 통일

---

## 관련 문서

- 현재 파이프라인: `translation_pipeline.md`
- 개선 파이프라인: `google_sheet_workflow.md`
- 워크플로우 비교: `workflow_comparison.md`
- 전체 분석 원본: `l10n_pipeline_redesign.md`

---

## 부록: 전체 Git 커밋 타임라인 (해결 대응 커밋만)

```
04-17 18:29  이경우       Sync lokalise all keys(수동)
04-17 20:19  이경우       test: deploy merged datasheet binary (keyword_test)
04-17 20:22  이경우       test: deploy merged datasheet binary (release/vng_test)
04-17 20:26  이경우       test: inject FK violation on keyword_test
04-17 20:45  이경우       test (x2)
04-17 20:53  이경우       binary update (1차)
04-17 20:59  이경우       binary update (2차 - linux 바이너리 신규 추가)
04-17 21:23  이경우       shell script 수정 (x3 브랜치)
04-17 21:41  이경우       fork lokalise 스크립트 수정 (x3 cherry-pick)
04-17 22:14  고지희       Sync lokalise all keys (1차)
04-17 22:18  고지희       Sync lokalise all keys (2차 재시도)
04-17 23:15  이상유       번역키 강제 업데이트 (x2 브랜치)
04-17 23:37  이상유       번역키 강제동기화 (x2 브랜치)
04-18 00:11  이상유       오탈자 수정 ← 21개 키 + 6종 오타 수정 본커밋
04-18 01:05  고지희       Sync lokalise specific keys (1차)
04-18 01:07  고지희       Sync lokalise specific keys (2차)
04-18 02:57  이경우       [I1] ui_string translations.pb rev 중복제거 ← datasheet 재컴파일!
04-18 03:38  이경우       [I1] ui_string translations.pb rev 중복제거 (x4 반복)
04-18 03:48  이경우       Sync lokalise specific keys
04-18 03:51  이경우       Sync lokalise specific keys
04-18 04:17  이경우       translations_lang.pb uistring rev 제거 ← 7개 언어 xlsx 대폭 증가
04-18 04:55  이경우       Sync lokalise specific keys
04-18 04:59  이경우       Sync lokalise specific keys
04-18 05:03  이경우       Sync lokalise specific keys (최종)
```
