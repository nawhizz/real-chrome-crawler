# Real Chrome Crawler

> 사용자의 **실제 Chrome 세션**(전용 디버그 프로필, 로그인 영속)을 CDP로 재사용해, 일반 자동화 브라우저가 봇 차단당하는 사이트의 페이지를 수집하고 **Obsidian 호환 Markdown + JSON**으로 정규화하는 **Claude Code Skill**.

기본 Playwright는 신규 프로필의 번들 Chromium을 띄워 ① 로그인 세션 부재 ② 자동화 시그널 노출로 봇 탐지에 걸린다. 본 도구는 디버깅 포트로 실행된 **실제 chrome.exe**에 `connect_over_cdp`로 attach해, 대상 사이트 입장에서는 진짜 사람의 트래픽과 구분되지 않게 한다.

- **상태**: v0.1 구현·검증 완료 (STEP-01 ~ STEP-05). v0.2 계획 진행 중.
- **지원 OS**: Windows 1순위 (macOS/Linux는 v0.2 stub).
- **런타임**: Python 3.12+ / [uv](https://docs.astral.sh/uv/) / Playwright(sync).

## 주요 특징

- **실제 Chrome 세션 재사용**: Chrome 136+ 정책 호환을 위해 비표준 `--user-data-dir`로 전용 디버그 프로필을 띄우고, 최초 1회 로그인 후 영속 유지한다.
- **브라우저 비파괴**: 세션 종료 시 우리가 연 탭만 닫고, 사용자의 기존 컨텍스트·Chrome 프로세스는 유지한다 (RD-8).
- **이중 산출물**: Obsidian YAML frontmatter + 출처 링크가 부착된 `.md`와 구조화 `.json`을 동시에 저장.
- **수집 가드**: robots.txt 확인 / 도메인 allowlist / polite delay 기본 탑재. robots 정책은 `warn`/`block`/`ignore` 선택 가능 (기본 `warn`).
- **자연어 자동 발동**: Claude Code Skill로 패키징되어 "이 URL 긁어줘", "옵시디언 노트로 클리핑" 같은 요청에 발동.

## 설치

```bash
git clone https://github.com/nawhizz/real-chrome-crawler.git
cd real-chrome-crawler
uv sync
```

수집 대상이 로그인을 요구하면 전용 프로필에 1회 로그인한다 (이후 영속):

```bash
uv run python -m scripts.chrome_launcher --wait-login
```

열린 Chrome 창에서 대상 사이트에 로그인 → 터미널에서 Enter.

## 사용법

엔드투엔드 수집 (가드 → 디버그 Chrome 확보 → attach → 수집 → 정규화 → 저장):

```bash
uv run python -m scripts.extractor "<URL>"
```

산출물은 `output/<slug>-<YYYYMMDD-HHMMSS>.md`와 동일 이름의 `.json`으로 저장된다.

### 옵션

| 옵션 | 설명 |
|------|------|
| `--auto-scroll` | 무한 스크롤/지연 로딩 대응 |
| `--robots-policy warn\|block\|ignore` | robots.txt 위반 시 동작 (기본 `warn`) |
| `--port <N>` | 디버그 포트 (기본 9222) |
| `--out-dir <PATH>` | 산출물 디렉터리 (기본 `output/`) |

### 보조 명령

```bash
# 디버그 Chrome만 띄우기
uv run python -m scripts.chrome_launcher
uv run python -m scripts.chrome_launcher --attach    # 이미 떠 있는 Chrome에 붙기만

# 수집만 (정규화 없이 HTML 길이 등 스모크 테스트)
uv run python -m scripts.collector "<URL>"
```

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

## 개발

```bash
uv run ruff check .
uv run mypy .
```

자세한 설계 결정과 단계별 구현 내역은 `docs/`의 PRD와 STEP 문서를 참조한다:

- `docs/PRD-real-chrome-crawler-v0.2.md` — 통합 결정(RD-1 ~ RD-13), Open Questions, v0.2 백로그
- `docs/STEP-01` ~ `STEP-05` — 단계별 구현 가이드

## 주의

- 본 기법 자체는 합법이나 대상 사이트의 **ToS · robots.txt · 개인정보 / 저작권** 법규 위반 소지가 있다. 특히 로그인 세션으로 회원 전용 콘텐츠를 수집하는 경우 약관 위반 가능성이 크다.
- 본인 데이터·공개 데이터·정당한 내부 용도 범위로 한정해 사용할 것.
- Chrome 정책 추가 변경 시 디버그 포트/프로필 동작이 바뀔 수 있다. 런타임 헬스체크로 조기 감지한다.

## 라이선스

미정.
