---
title: STEP-01 — 프로젝트 스캐폴딩
project: real-chrome-crawler
step: 1
status: ready
date: 2026-06-03
tags:
  - claude-code
  - step
  - scaffolding
---

# STEP-01 — 프로젝트 스캐폴딩

> [!info] 목표
> `real-chrome-crawler` Claude Skill의 프로젝트 골격을 만든다. **uv 초기화 → Python 3.12 고정 → Playwright(Python) 설치 → Package by Feature 디렉터리 + placeholder 파일 → 검증**까지.

> [!note] 확정된 전제 (Resolved Decisions)
> - 1순위 OS = **Windows**
> - 프로필 전략 = **전용 디버그 프로필**(1회 로그인), `--attach` 옵션 제공 *(RD-4 수정 반영)*
> - robots.txt 위반 = **경고 후 진행**
> - Runtime = **Python 3.12+ / uv / Playwright(Python, sync API)**

> [!warning] Playwright 브라우저 바이너리는 설치하지 않는다
> 본 스킬은 사용자의 **실제 Chrome**에 `connect_over_cdp`로 붙으므로 Playwright 번들 Chromium이 필요 없다. `playwright install` 은 **실행하지 말 것** (수백 MB 절약).

---

## 실행 절차

아래 명령을 순서대로 실행한다. (Windows / PowerShell 기준, uv 설치 가정)

### 1. 프로젝트 생성 & Python 고정

```powershell
uv init real-chrome-crawler
cd real-chrome-crawler
uv python pin 3.12
```

### 2. 의존성 추가 (브라우저 바이너리 설치 없이)

```powershell
uv add playwright
uv add --dev ruff mypy
```

> [!tip]
> `uv add playwright` 는 pip 패키지만 설치한다. `playwright install` 은 호출하지 않는다.

### 3. 디렉터리 구조 & placeholder 생성

다음 구조를 만든다. 각 placeholder 파일에는 한 줄짜리 docstring/주석만 넣어 STEP 매핑을 표시한다.

```
real-chrome-crawler/
├── SKILL.md                  # STEP-05에서 작성
├── pyproject.toml            # uv가 생성/관리
├── README.md                 # 간단 설명 (아래 내용으로 작성)
├── scripts/
│   ├── __init__.py
│   ├── chrome_launcher.py    # STEP-02: 전용 디버그 프로필 + 디버깅 포트 실행
│   ├── cdp_session.py        # STEP-03: connect_over_cdp attach / 안전 종료
│   ├── collector.py          # STEP-03: page.goto + 대기 전략 + HTML 수집
│   ├── extractor.py          # STEP-04: HTML → Obsidian MD + JSON
│   └── guards.py             # STEP-04: robots.txt / rate limit / allowlist
└── references/
    └── selectors.md          # 사이트별 셀렉터 메모 (점증)
```

각 `*.py` placeholder 예시:

```python
"""chrome_launcher.py — STEP-02에서 구현 예정.

전용 비표준 user-data-dir로 진짜 Chrome을 --remote-debugging-port와
함께 실행한다 (1회 로그인 후 영속, Windows 1순위).
"""
```

`references/selectors.md` (구조화 템플릿 — 실제 규칙은 비워둔 stub):

```markdown
# Site Selectors & Wait Strategies

수집 전 이 문서를 확인해, 대상 도메인에 규칙이 있으면 참고/적용한다.
새로 검증한 사이트는 아래 형식으로 추가한다.
(v0.1: 검증된 실제 사이트 없음 → 예시 외 비어 있음)

## 형식

도메인별 블록으로 기록한다:

- **domain**: 적용 호스트 (예: `news.example.com`)
- **content_selector**: 본문 영역 CSS 셀렉터 (없으면 전체 body)
- **wait_for**: goto 후 기다릴 셀렉터/조건 (선택)
- **auto_scroll**: 무한 스크롤/지연 로딩 여부 (true/false → `--auto-scroll`)
- **notes**: 특이사항(로그인 필요, 동적 로딩, 차단 회피 메모 등)

## 예시 (템플릿일 뿐, 실제 적용 규칙 아님)

### example.com
- content_selector: `main`
- wait_for: `h1`
- auto_scroll: false
- notes: 정적 데모 페이지. 형식 예시용.

<!-- 첫 실제 사이트 검증 후 여기에 도메인 블록을 추가한다 -->
```

> [!tip] 이미 STEP-01을 실행한 경우
> 디렉터리/패키지는 그대로 두고, `references/selectors.md` **이 파일 내용만** 위 템플릿으로 교체하면 된다.

`README.md` 내용:

```markdown
# real-chrome-crawler

사용자의 실제 Chrome 세션(CDP)을 재사용해 봇 차단 사이트를 수집하고
Obsidian 호환 Markdown + JSON으로 정규화하는 Claude Code Skill.

⚠️ 대상 사이트의 ToS·robots.txt·관련 법규를 준수해 사용할 것.
```

### 4. 검증

```powershell
uv run python -c "import playwright; from importlib.metadata import version; print('playwright', version('playwright'))"
uv run ruff --version
```

---

## 완료 기준 (Definition of Done)

- [ ] `uv run python -c "import playwright"` 가 오류 없이 버전을 출력
- [ ] 위 디렉터리 구조·placeholder 파일이 모두 존재
- [ ] `pyproject.toml` 의 `requires-python` 이 `>=3.12`
- [ ] `playwright install` 은 실행하지 않았음(번들 브라우저 없음)

---

## 결과 회신 양식

> [!todo] 실행 후 아래 표를 채워 회신해 주세요

| 항목 | 결과 | 비고 |
|------|------|------|
| Python 버전 (`uv run python -V`) | | 3.12.x 기대 |
| Playwright 버전 | | |
| ruff 버전 | | |
| 디렉터리 구조 생성 | 완료 / 일부 / 실패 | |
| `pyproject.toml` requires-python | | `>=3.12` 기대 |
| 오류/경고 메시지 | | 있으면 원문 첨부 |

회신 주시면 검증 후 **STEP-02 (`chrome_launcher.py` — 핵심)** instruction을 생성하겠습니다.
