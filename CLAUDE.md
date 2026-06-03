# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 명령어

```bash
# 의존성 설치
uv sync

# 페이지 수집 (엔드투엔드 - 주 진입점)
uv run python -m scripts.extractor "<URL>"

# 옵션
uv run python -m scripts.extractor "<URL>" --auto-scroll --robots-policy warn|block|ignore --port 9222 --out-dir output

# 디버그 Chrome 실행 (최초 1회 또는 별도 실행 시)
uv run python -m scripts.chrome_launcher
uv run python -m scripts.chrome_launcher --wait-login   # 로그인 대기
uv run python -m scripts.chrome_launcher --attach       # 이미 떠 있는 Chrome에만 붙기

# HTML 수집만 (extractor 없이 스모크 테스트)
uv run python -m scripts.collector "<URL>"

# 린트 / 타입 체크
uv run ruff check .
uv run mypy .
```

## 아키텍처

실행 흐름: `extractor.main()` → `guards.evaluate()` → `chrome_launcher.ensure_chrome()` → `cdp_session.cdp_attach()` → `collector.collect_page()` → `extractor.save_outputs()`

### 모듈 역할

| 모듈 | 역할 |
|------|------|
| `scripts/chrome_launcher.py` | 비표준 user-data-dir로 실제 chrome.exe 실행. 포트가 이미 열려 있으면 재사용(idempotent). Windows 전용(v0.1). |
| `scripts/cdp_session.py` | `connect_over_cdp`로 실행 중인 Chrome에 attach. `CdpSession`이 우리가 연 탭만 추적·정리하고 브라우저/기존 컨텍스트는 건드리지 않는다(RD-8). |
| `scripts/collector.py` | `page.goto` + 대기 + auto_scroll. 결과를 `PageResult` dataclass로 반환. |
| `scripts/extractor.py` | BeautifulSoup으로 노이즈 태그 제거 → markdownify 변환 → YAML frontmatter 부착 → `output/` 에 `.md` + `.json` 저장. 주 CLI 진입점. |
| `scripts/guards.py` | robots.txt 확인 / 도메인 allowlist / polite delay. `blocked=True`면 수집 중단. |
| `scripts/console.py` | Windows CP949 터미널 대응 UTF-8 stdio 설정 유틸. |

### 핵심 설계 원칙

- **실제 Chrome 세션 재사용**: 봇 차단 우회를 위해 Playwright 자체 브라우저가 아닌 실행 중인 chrome.exe에 CDP로 attach한다.
- **브라우저 비파괴**: 세션 종료 시 우리가 연 탭만 닫고, 사용자의 기존 컨텍스트·Chrome 프로세스는 유지한다.
- **전용 프로필**: `%LOCALAPPDATA%/real-chrome-crawler/chrome-profile/`에 영속 저장되는 비표준 디렉터리 사용(Chrome 136+ 정책 호환).

### 산출물

`output/<slug>-<YYYYMMDD-HHMMSS>.md` (Obsidian YAML frontmatter 포함) + 동일 이름 `.json`

## 사이트별 수집 규칙

새 도메인 검증 후 `references/selectors.md`에 도메인 블록을 추가한다(형식은 해당 파일 참조).
