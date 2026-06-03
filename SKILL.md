---
name: real-chrome-crawler
description: >-
  사용자의 실제 Chrome 세션(로그인·쿠키)을 재사용해, 일반 자동화 브라우저가 봇으로
  차단당하는 사이트의 페이지를 수집하고 Obsidian 호환 Markdown + JSON으로 저장한다.
  "이 사이트 자료 좀 모아줘", "이 URL 긁어줘/스크래핑/클리핑/크롤링", "로그인해야 보이는
  페이지 수집", "차단되는 사이트 자료 수집", "웹페이지를 마크다운으로 저장" 같은 요청에 사용.
  Use when the user wants to scrape, clip, or collect a web page — especially one that
  blocks normal automation or requires a logged-in session — and save it as Markdown/JSON.
argument-hint: [url]
---

# Real Chrome Crawler

실행 중인 **실제 Chrome**(전용 디버그 프로필)에 CDP로 attach해 페이지를 수집하고,
Obsidian 호환 노트로 저장한다. 진짜 브라우저 세션이라 봇 차단을 우회한다.

## 최초 1회 설정

1. 의존성 동기화:

```bash
   cd "${CLAUDE_SKILL_DIR}" && uv sync
```

2. 전용 프로필 로그인(수집 대상이 로그인 필요 시):

```bash
   cd "${CLAUDE_SKILL_DIR}" && uv run python -m scripts.chrome_launcher --wait-login
```

열린 Chrome 창에서 대상 사이트에 로그인 후 Enter. 이후 영속 유지된다.

## 수집 실행

대상 URL을 `<URL>` 자리에 넣어 실행한다(직접 호출 시 `$ARGUMENTS`가 URL):

```bash
cd "${CLAUDE_SKILL_DIR}" && uv run python -m scripts.extractor "<URL>"
```

- 산출물: `${CLAUDE_SKILL_DIR}/output/<slug>-<timestamp>.md` (Obsidian) + 동일 이름 `.json`
- 실행 후 저장 경로를 사용자에게 보고하고, 요청 시 `.md` 본문을 요약한다.
- 첫 bash 실행은 권한 승인을 물을 수 있다(정상).

## 옵션

- 지연 로딩/무한 스크롤: `--auto-scroll`
- robots 정책: `--robots-policy warn|block|ignore` (기본 `warn` = 경고 후 진행)
- 포트 변경: `--port <N>` (기본 9222)
- 이미 띄운 디버그 Chrome에 붙기: `chrome_launcher --attach`

## 주의

- 대상 사이트의 ToS·robots.txt·개인정보/저작권 법규를 준수할 것. 회원 전용 콘텐츠
  수집은 약관 위반 소지가 있다.
- 사이트별 본문 셀렉터·대기 전략은 [references/selectors.md](references/selectors.md)에 점증 기록한다.
