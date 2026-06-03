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

먼저 [references/selectors.md](references/selectors.md)에서 대상 도메인 규칙을 확인한다.
**규칙이 있으면 반드시 해당 필드를 CLI 옵션으로 변환해 붙인다.** (이 변환을 빠뜨리면
본문 대신 페이지 전체가 추출되어 노이즈가 섞인다.)

- `content_selector: <셀렉터>` → `--content-selector "<셀렉터>"`
- `auto_scroll: true` → `--auto-scroll`

예) `n.news.naver.com`은 `content_selector: #dic_area` 규칙이 있으므로
`--content-selector "#dic_area"`를 붙여 본문(`#dic_area`)만 추출한다.

대상 URL을 `<URL>` 자리에 넣어 실행한다(직접 호출 시 `$ARGUMENTS`가 URL).
selectors.md 규칙이 있으면 위 변환 결과를 함께 붙인다:

```bash
cd "${CLAUDE_SKILL_DIR}" && uv run python -m scripts.extractor "<URL>" [--content-selector "<셀렉터>"] [--auto-scroll]
```

규칙이 없으면 옵션 없이 실행한다(전체 body에서 노이즈 태그 제거 후 추출):

```bash
cd "${CLAUDE_SKILL_DIR}" && uv run python -m scripts.extractor "<URL>"
```

- 산출물: `${CLAUDE_SKILL_DIR}/output/<slug>-<timestamp>.md` (Obsidian) + 동일 이름 `.json`
- 실행 후 저장 경로를 사용자에게 보고하고, 요청 시 `.md` 본문을 요약한다.
- 첫 bash 실행은 권한 승인을 물을 수 있다(정상).

## 옵션

- 본문 셀렉터: `--content-selector "<CSS>"` (지정 시 해당 요소만 추출, 노이즈 제거에 가장 효과적.
  예: 네이버 뉴스 `--content-selector "#dic_area"`. 미지정 시 전체 body에서 노이즈 태그만 제거)
- 지연 로딩/무한 스크롤: `--auto-scroll`
- robots 정책: `--robots-policy warn|block|ignore` (기본 `warn` = 경고 후 진행)
- 포트 변경: `--port <N>` (기본 9222)
- 이미 띄운 디버그 Chrome에 붙기: `chrome_launcher --attach`

## 주의

- 대상 사이트의 ToS·robots.txt·개인정보/저작권 법규를 준수할 것. 회원 전용 콘텐츠
  수집은 약관 위반 소지가 있다.
- [references/selectors.md](references/selectors.md): 수집 전 대상 도메인 규칙을 확인·적용하고,
  새로 검증한 사이트의 본문 셀렉터·대기 전략은 같은 형식으로 추가 기록한다.
