# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 명령어

```bash
# 의존성 설치 (playwright install은 절대 실행하지 말 것 — 아래 "주의" 참조)
uv sync

# 엔드투엔드 수집 (주 진입점: 가드 → Chrome 확보 → attach → 수집 → 정규화 → 저장)
uv run python -m scripts.extractor "<URL>"
uv run python -m scripts.extractor "<URL>" --auto-scroll --robots-policy warn|block|ignore --port 9222 --out-dir output

# 디버그 Chrome 단독 실행
uv run python -m scripts.chrome_launcher                # 기본
uv run python -m scripts.chrome_launcher --wait-login   # 최초 1회 로그인 대기
uv run python -m scripts.chrome_launcher --attach       # 이미 떠 있는 Chrome에 붙기만

# HTML 수집만 (정규화 없이 스모크 테스트)
uv run python -m scripts.collector "<URL>"

# 린트 / 타입 체크 (테스트 스위트는 아직 없음)
uv run ruff check .
uv run mypy .
```

## 아키텍처

실행 흐름: `extractor.main()` → `guards.evaluate()` → `chrome_launcher.ensure_chrome()` → `cdp_session.cdp_attach()` → `collector.collect_page()` → `extractor.html_to_markdown()` → `extractor.save_outputs()`

### 모듈 역할

| 모듈 | 역할 |
|------|------|
| `scripts/chrome_launcher.py` | 비표준 `--user-data-dir`로 실제 chrome.exe 실행. 포트가 이미 살아있으면 재사용(idempotent). Windows 전용(v0.1, macOS/Linux는 `NotImplementedError` stub). |
| `scripts/cdp_session.py` | `connect_over_cdp`로 attach. `CdpSession`이 우리가 연 탭만 추적·정리하고 브라우저/기존 컨텍스트는 건드리지 않는다 (RD-8). 기존 `browser.contexts[0]`(로그인 컨텍스트)을 재사용. |
| `scripts/collector.py` | `page.goto` + 대기 + `auto_scroll`. 결과를 `PageResult` dataclass로 반환. |
| `scripts/extractor.py` | BeautifulSoup으로 노이즈 태그 제거 → markdownify 변환 → YAML frontmatter 부착 → `output/` 에 `.md` + `.json` 저장. 주 CLI 진입점. |
| `scripts/guards.py` | robots.txt 확인 / 도메인 allowlist / polite delay. `blocked=True`면 호출측이 수집 중단. robots 정책 기본값은 `warn`(경고 후 진행). |
| `scripts/console.py` | Windows CP949 터미널 대응 UTF-8 stdio 설정 유틸. **import 부작용 금지 — 각 CLI `main()` 시작에서 명시 호출**한다 (RD-11). |

### 핵심 설계 원칙

- **실제 Chrome 세션 재사용 (RD-3)**: 봇 차단 우회를 위해 Playwright 번들 Chromium이 아닌 실행 중인 chrome.exe에 CDP로 attach한다.
- **전용 디버그 프로필 (RD-4)**: Chrome 136+ 정책상 `--remote-debugging-port`는 기본 데이터 디렉터리에서 무시되며 비표준 `--user-data-dir` 필수. 메인 프로필 쿠키 복호화도 불가하므로, `%LOCALAPPDATA%/real-chrome-crawler/chrome-profile/`에 전용 디버그 프로필을 만들어 1회 로그인 후 영속 재사용한다.
- **브라우저 비파괴 (RD-8)**: 세션 종료 시 우리가 연 탭만 닫고, 사용자의 기존 컨텍스트·Chrome 프로세스는 유지한다.
- **CLI UTF-8 강제 (RD-11)**: `scripts/console.ensure_utf8_stdio()`를 import 부작용으로 두지 말고 각 진입점 `main()` 첫 줄에서 호출한다 (ruff E402 회피 + 부작용 격리).
- **Package by Feature (RD-5)**: 모듈을 기능 단위로 분리.

### 산출물

`output/<slug>-<YYYYMMDD-HHMMSS>.md` (Obsidian YAML frontmatter + 출처 링크) + 동일 이름 `.json`. `output/`은 `.gitignore` 대상.

## 주의 (작업 시 자주 실수하는 지점)

- **`playwright install` 금지**: 본 프로젝트는 사용자의 실제 Chrome에 attach만 하므로 번들 Chromium이 불필요하다. 실수로 실행하면 수백 MB가 설치된다.
- **메인 Chrome 프로필 직접 사용 금지**: Chrome 136+ 정책 위반이며 페이지 미로딩·브라우저 종료가 발생한다. 항상 `chrome_launcher`가 만드는 전용 프로필을 사용.
- **`browser.close()` 호출 금지**: 우리가 띄운 게 아닌 사용자 Chrome일 수 있다. `CdpSession.cleanup()`은 탭만 닫고 `pw.stop()`으로 드라이버만 정리한다.
- **import-time 부작용 추가 금지**: stdio reconfigure 등은 반드시 `main()` 내부에서. ruff E402와 충돌하고 라이브러리로 import될 때 부작용을 일으킨다.

## 사이트별 수집 규칙

수집 전 `references/selectors.md`에서 대상 도메인 규칙을 확인하고, 새 사이트 검증 후 같은 형식으로 추가 기록한다 (RD-12). `content_selector` 자동 적용은 v0.2 백로그(OQ-7).

## 언어 규칙

- 응답 / 커밋 메시지 / 코드 주석 / 문서는 **한국어** (전역 CLAUDE.md 규약).
- 변수명·함수명·식별자는 영어 유지.

## 추가 컨텍스트

- 설계 의사결정(RD-1 ~ RD-13)과 Open Questions: `docs/PRD-real-chrome-crawler-v0.2.md`
- 단계별 구현 가이드: `docs/STEP-01-scaffolding.md` ~ `docs/STEP-05-skill-md-packaging.md`
- 본 저장소는 Claude Code Skill 소스다. 설치 검증은 별도 테스트 프로젝트의 `.claude/skills/`에서 수행하고 여기는 편집하지 않는다 (RD-13).
