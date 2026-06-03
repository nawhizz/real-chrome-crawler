# Real Chrome Crawler

> 사용자의 **실제 Chrome 세션**(전용 디버그 프로필, 로그인 영속)을 CDP로 재사용해, 일반 자동화 브라우저가 봇 차단당하는 사이트의 페이지를 수집하고 **Obsidian 호환 Markdown + JSON**으로 정규화하는 **Claude Code Skill**.

기본 Playwright는 신규 프로필의 번들 Chromium을 띄워 ① 로그인 세션 부재 ② 자동화 시그널 노출로 봇 탐지에 걸린다. 본 도구는 디버깅 포트로 실행된 **실제 chrome.exe**에 `connect_over_cdp`로 attach해, 대상 사이트 입장에서는 진짜 사람의 트래픽과 구분되지 않게 한다.

- **상태**: v0.1 구현·검증 완료 (STEP-01 ~ STEP-05). v0.2 계획 진행 중.
- **지원 OS**: Windows 1순위 (macOS/Linux는 v0.2 stub).
- **런타임**: Python 3.12+ / [uv](https://docs.astral.sh/uv/) / Playwright(sync).

## 무엇이 이 프로젝트인가

본 저장소는 **[Claude Code Skill](https://code.claude.com/docs/ko/skills) 소스**다. Claude Code Skill은 Claude Code 환경에서 자연어 요청이나 슬래시 명령으로 발동되는 재사용 가능한 작업 단위이며, `SKILL.md`의 `description`에 정의된 트리거 문구로 자동 발동된다.

이 저장소는 두 방식으로 사용할 수 있다:

1. **Claude Code Skill로 설치** (권장) — 자연어로 "이 URL 긁어줘"라고 요청하면 Claude Code가 자동 발동.
2. **CLI 직접 실행** (개발/디버그) — `uv run python -m scripts.extractor "<URL>"`.

아래는 Skill 설치·사용을 우선으로 다룬다. CLI 사용은 본 문서 후반의 [개발 / CLI 직접 실행](#개발--cli-직접-실행-디버그용) 섹션 참조.

---

## 사전 요구사항

- Windows 10/11
- [uv](https://docs.astral.sh/uv/) (Python 3.12+ 관리)
- Google Chrome (표준 설치 경로)
- Claude Code

## 설치 — 프로젝트 스코프 Skill

> Claude Code 프로젝트 스코프 스킬은 `<프로젝트>/.claude/skills/<name>/SKILL.md` 형태로 배치되며, 해당 프로젝트에서 Claude Code를 켰을 때만 로드된다. 다른 작업 중 오발동을 막기 위해 **별도 테스트 프로젝트**에 설치하는 것을 권장한다.

```powershell
# 1) 테스트 프로젝트 생성
mkdir %USERPROFILE%\projects\rcc-test
cd %USERPROFILE%\projects\rcc-test

# 2) 본 저장소의 소스만 .claude/skills/real-chrome-crawler 로 복사
#    <DEV> = 본 저장소를 git clone 한 절대 경로
#    robocopy는 0~7 종료코드가 정상 (경고로 보지 말 것)
robocopy "<DEV>" ".\.claude\skills\real-chrome-crawler" /E ^
  /XD .git .venv output __pycache__ .ruff_cache .mypy_cache ^
  /XF *.pyc

# 3) 설치처에서 의존성 동기화 (독립 .venv 생성)
cd .claude\skills\real-chrome-crawler
uv sync
cd %USERPROFILE%\projects\rcc-test
```

> **`.venv`를 그대로 복사하지 말 것.** uv 가상환경은 경로가 박혀 있어 복사하면 깨진다. 위처럼 `.venv`/`.git`/`output`/캐시를 제외하고 설치처에서 `uv sync`로 새로 만든다.

> **`playwright install` 금지.** 본 스킬은 사용자의 실제 Chrome에 attach만 하므로 Playwright 번들 Chromium이 불필요하다.

설치 후 테스트 프로젝트에서 Claude Code를 실행하면 워크스페이스 신뢰(trust) 수락 후 스킬이 로드된다.

```powershell
cd %USERPROFILE%\projects\rcc-test
claude
```

## 최초 1회 로그인 (수집 대상이 로그인을 요구하는 경우)

본 스킬은 `${CLAUDE_SKILL_DIR}` 환경변수로 자신의 설치 경로를 참조한다 (Claude Code Skill 표준 — 설치 위치 무관). 전용 디버그 프로필에 1회 로그인하면 이후 영속 유지된다.

Claude Code 세션 안에서 다음 bash 실행:

```bash
cd "${CLAUDE_SKILL_DIR}" && uv run python -m scripts.chrome_launcher --wait-login
```

열린 Chrome 창에서 대상 사이트에 로그인 → 터미널에서 Enter. 이후 영속 저장되어 다음 실행부터 로그인이 유지된다.

## 사용 — 자연어 발동

설치 후 Claude Code에 다음과 같은 자연어 요청을 하면 스킬이 자동 발동한다 (URL을 실제 주소로 교체):

- "이 사이트 자료 좀 모아줘 https://example.com"
- "https://example.com 이 URL 긁어줘 / 스크래핑 / 클리핑 / 크롤링"
- "로그인해야 보이는 페이지 수집 https://example.com"
- "차단되는 사이트 자료 수집 https://example.com"
- "https://example.com 을 마크다운으로 저장"

스킬이 실행되면 산출물 경로(`output/<slug>-<timestamp>.md` 및 `.json`)를 보고한다.

## 사용 — 슬래시 명령 직접 호출

스킬 이름이 곧 슬래시 명령이다. URL은 `$ARGUMENTS`로 전달된다.

```text
/real-chrome-crawler https://example.com
```

## 옵션

| 옵션 | 설명 |
|------|------|
| `--auto-scroll` | 무한 스크롤/지연 로딩 대응 |
| `--content-selector <CSS>` | 본문 영역만 추출 (예: 네이버 뉴스 → `#dic_area`) |
| `--robots-policy warn\|block\|ignore` | robots.txt 위반 시 동작 (기본 `warn`) |
| `--port <N>` | 디버그 포트 (기본 9222) |
| `--out-dir <PATH>` | 산출물 디렉터리 (기본 `output/`) |

### 사이트별 권장 옵션

| 사이트 | 옵션 |
|--------|------|
| 네이버 뉴스 (`n.news.naver.com`) | `--content-selector "#dic_area"` |

자연어 요청 안에 "스크롤 해서", "robots 무시하고" 같은 문구를 넣으면 Claude Code가 해당 옵션을 추론해 적용한다. 직접 제어가 필요하면 슬래시 명령에 옵션을 함께 전달하거나 CLI로 호출.

## 산출물

`output/<slug>-<YYYYMMDD-HHMMSS>.md`(Obsidian YAML frontmatter + 출처 링크) + 동일 이름 `.json`.

```yaml
---
title: "페이지 제목"
source: https://example.com/
fetched: 2026-06-03
status: 200
tags:
  - clipped
---
```

## 배포 — 비공개 GitHub 마켓플레이스 (선택)

여러 환경에서 "한 줄 설치"로 재사용하려면 마켓플레이스로 배포한다.

스킬 루트에 `.claude-plugin/plugin.json`:

```json
{
  "name": "real-chrome-crawler",
  "version": "0.1.0",
  "description": "실제 Chrome 세션 재사용 크롤러 — Obsidian MD/JSON 출력"
}
```

리포 루트에 `.claude-plugin/marketplace.json`:

```json
{
  "name": "<your-marketplace-name>",
  "owner": { "name": "<your-name>" },
  "plugins": [
    {
      "name": "real-chrome-crawler",
      "source": "./real-chrome-crawler",
      "version": "0.1.0",
      "description": "실제 Chrome 세션 재사용 크롤러"
    }
  ]
}
```

비공개 GitHub push 후, 다른 환경의 Claude Code에서:

```text
/plugin marketplace add <github-user>/<repo>
/plugin install real-chrome-crawler@<your-marketplace-name>
```

설치처에서 `uv sync` 1회 필요(런타임 의존성).

---

## 개발 / CLI 직접 실행 (디버그용)

스킬을 거치지 않고 본 저장소에서 직접 CLI로 실행할 수 있다.

```bash
git clone https://github.com/nawhizz/real-chrome-crawler.git
cd real-chrome-crawler
uv sync
```

엔드투엔드 수집 (가드 → 디버그 Chrome 확보 → attach → 수집 → 정규화 → 저장):

```bash
uv run python -m scripts.extractor "<URL>"
uv run python -m scripts.extractor "<URL>" --auto-scroll --robots-policy warn --port 9222 --out-dir output
```

### 보조 명령

```bash
# 디버그 Chrome만 띄우기
uv run python -m scripts.chrome_launcher
uv run python -m scripts.chrome_launcher --wait-login   # 최초 1회 로그인 대기
uv run python -m scripts.chrome_launcher --attach       # 이미 떠 있는 Chrome에 붙기만

# 수집만 (정규화 없이 스모크 테스트)
uv run python -m scripts.collector "<URL>"
```

### 린트 / 타입 체크

```bash
uv run ruff check .
uv run mypy .
```

---

## 아키텍처

```
real-chrome-crawler/
├── SKILL.md                  # Claude Code Skill 트리거 + 워크플로우
├── pyproject.toml            # uv, Python 3.12+, ruff/mypy
├── scripts/
│   ├── console.py            # CLI UTF-8 stdio (Windows CP949 대응)
│   ├── chrome_launcher.py    # 전용 디버그 프로필 + --remote-debugging-port
│   ├── cdp_session.py        # connect_over_cdp attach / 우리 page만 정리
│   ├── collector.py          # page.goto + 대기 전략 + auto_scroll + HTML 수집
│   ├── extractor.py          # HTML → Obsidian MD + JSON (주 진입점)
│   └── guards.py             # robots.txt / rate limit / domain allowlist
├── references/
│   └── selectors.md          # 도메인별 규칙 (읽기·적용·기록)
└── docs/                     # PRD + STEP 문서
```

### 실행 흐름

```
사용자 요청 (URL)
   └─ guards.evaluate           robots / allowlist 확인 (blocked면 중단)
   └─ chrome_launcher.ensure_chrome  포트 응답하면 재사용, 없으면 실행
   └─ cdp_session.cdp_attach    connect_over_cdp + 기존 컨텍스트 재사용
   └─ collector.collect_page    page.goto + 대기 + auto_scroll + HTML
   └─ extractor.html_to_markdown 노이즈 태그 제거 + markdownify
   └─ extractor.save_outputs    Obsidian MD + JSON 동시 저장
   └─ 종료: 우리가 연 탭만 close, 브라우저 유지
```

## 사이트별 수집 규칙

`references/selectors.md`에 도메인별 `content_selector` / `wait_for` / `auto_scroll` / `notes`를 기록한다.
수집 전 이 문서를 먼저 확인해 규칙이 있으면 옵션에 반영하고, 새로 검증한 사이트는 같은 형식으로 추가한다.

> v0.1은 템플릿만 존재. `content_selector` 자동 적용은 v0.2 백로그(OQ-7).

## 추가 문서

- `docs/PRD-real-chrome-crawler-v0.2.md` — 통합 결정(RD-1 ~ RD-13), Open Questions, v0.2 백로그
- `docs/STEP-01` ~ `STEP-05` — 단계별 구현 가이드
- `SKILL.md` — 스킬 frontmatter, 워크플로우 정의 (소스 진실)

## 주의

- 본 기법 자체는 합법이나 대상 사이트의 **ToS · robots.txt · 개인정보 / 저작권** 법규 위반 소지가 있다. 특히 로그인 세션으로 회원 전용 콘텐츠를 수집하는 경우 약관 위반 가능성이 크다.
- 본인 데이터·공개 데이터·정당한 내부 용도 범위로 한정해 사용할 것.
- Chrome 정책 추가 변경 시 디버그 포트/프로필 동작이 바뀔 수 있다. 런타임 헬스체크로 조기 감지한다.

## 라이선스

미정.
