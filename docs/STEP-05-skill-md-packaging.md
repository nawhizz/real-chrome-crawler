---
title: STEP-05 — SKILL.md 작성 + 테스트 프로젝트 검증
project: real-chrome-crawler
step: 5
status: ready
date: 2026-06-03
tags:
  - claude-code
  - step
  - skill-md
  - testing
  - obsidian
---

# STEP-05 — `SKILL.md` 작성 + 테스트 프로젝트 검증 *(마무리)*

> [!abstract] 목표
> 지금까지의 모듈을 자연어 요청에 자동 발동되는 **Claude Code Skill**로 묶고, **개발 소스와 분리된 별도 테스트 프로젝트**의 프로젝트 스코프 스킬로 설치해 검증한다. 배포(재사용)는 그 다음.

> [!note] 분리 원칙 (왜 별도 테스트 프로젝트인가)
> - **개발 폴더** = source of truth(편집·git). 여기서 직접 설치 테스트하지 않는다.
> - **테스트 프로젝트의 `.claude/skills/`** = 프로젝트 스코프 → 그 폴더에서 Claude Code를 켰을 때만 로드. 다른 작업 중 오발동·미검증본 전역 노출이 없다.
> - 메모리 원칙(프로토타입 ≠ MVP, 검증 자산 분리)과 동일한 결.

> [!note] Claude Code 스킬 사실(공식 문서)
> - 프로젝트 스킬 경로 = `<project>/.claude/skills/<name>/SKILL.md` → 명령 이름은 디렉터리명(`/real-chrome-crawler`)
> - 스크립트는 **`${CLAUDE_SKILL_DIR}`** 로 참조 → 설치 위치 무관
> - 프로젝트 `.claude/skills/`는 시작 디렉터리와 상위 디렉터리에서 로드. 워크스페이스 신뢰(trust) 수락 필요

---

## 0. 산출물 결함 수정 (H1 중복)

현재 `.md`에 제목 H1이 두 번 찍힌다(우리가 넣은 `# 제목` + 본문 자체 H1). `scripts/extractor.py`를 패치한다.

**(a) `to_obsidian_note` 위에 헬퍼 추가:**

```python
def _strip_leading_h1(body: str, title: str) -> str:
    """본문 첫 H1이 제목과 동일하면 제거(중복 방지)."""
    match = re.match(r"\s*#\s+(.+?)\s*\n", body)
    if match and match.group(1).strip().lower() == title.strip().lower():
        return body[match.end():].lstrip("\n")
    return body
```

**(b) `to_obsidian_note`의 `return` 부분 교체:**

```python
    body = _strip_leading_h1(body_md, result.title)
    return (
        f"{frontmatter}\n# {result.title}\n\n"
        f"출처: <{result.final_url}>\n\n{body}\n"
    )
```

재확인:

```powershell
uv run python -m scripts.extractor https://example.com
type output\*.md   # H1이 한 번만 나오는지 확인
uv run ruff check scripts/extractor.py
```

---

## 1. `SKILL.md` 작성 (개발 폴더 루트)

개발 폴더 루트의 `SKILL.md`를 아래 내용으로 작성한다(이것이 소스 진실).

````markdown
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
규칙이 있으면 참고해 옵션을 정한다(예: `auto_scroll: true` → `--auto-scroll`).

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
- [references/selectors.md](references/selectors.md): 수집 전 대상 도메인 규칙을 확인·적용하고,
  새로 검증한 사이트의 본문 셀렉터·대기 전략은 같은 형식으로 추가 기록한다.
````

> [!tip] description 설계 의도
> 한국어 트리거 문구를 앞쪽에, 핵심 use case를 먼저 배치했다(`description`+`when_to_use` 합산 1,536자에서 잘릴 수 있어 앞부분이 중요). 스킬은 과소 발동 경향이 있어 약간 "적극적"으로 적었다.

---

## 2. 별도 테스트 프로젝트 만들기 + 설치

> [!warning] 개발 폴더를 그대로 복사하지 말 것
> `.venv`(uv 가상환경)는 경로가 박혀 있어 복사 시 깨진다. `.git`/`output`/캐시도 제외하고 **소스만** 복사한 뒤 설치처에서 `uv sync`로 환경을 새로 만든다.

```powershell
# 1) 테스트 프로젝트 생성
mkdir %USERPROFILE%\projects\rcc-test
cd %USERPROFILE%\projects\rcc-test

# 2) 프로젝트 스코프 스킬 폴더로 '소스만' 복사 (robocopy로 제외 처리)
#    <DEV> = 개발 폴더 절대경로. robocopy는 0~7 종료코드가 정상이므로 경고로 보지 말 것.
robocopy "<DEV>" ".\.claude\skills\real-chrome-crawler" /E ^
  /XD .git .venv output __pycache__ .ruff_cache .mypy_cache ^
  /XF *.pyc

# 3) 설치처에서 의존성 동기화 (독립 .venv 생성)
cd .claude\skills\real-chrome-crawler
uv sync
cd %USERPROFILE%\projects\rcc-test
```

> [!tip] 빠른 반복이 필요하면(선택)
> 복사 대신 심볼릭 링크: `mklink /D "%CD%\.claude\skills\real-chrome-crawler" "<DEV>"`. 편집이 즉시 반영돼 SKILL.md 텍스트 수정 반복에 편하다. 단 이건 "연결"이라 분리 검증 목적이면 **최종 1회는 복사본으로** 다시 확인할 것.

---

## 3. 테스트 (발동 + 동작)

테스트 프로젝트 폴더에서 Claude Code를 시작하고(워크스페이스 신뢰 수락) 검증한다.

```powershell
cd %USERPROFILE%\projects\rcc-test
claude
```

```text
# (A) 직접 호출
/real-chrome-crawler https://example.com
```

> [!todo] 자동 발동 테스트 프롬프트 3종
> 1. "이 사이트 자료 좀 모아줘 https://example.com"
> 2. "https://example.com 를 옵시디언 노트로 클리핑해줘"
> 3. "로그인한 상태로 보이는 이 페이지 긁어줄래? <URL>"

각 케이스에서 스킬이 발동되어 산출물이 생성되면 성공. 발동이 약하면 개발 폴더의 `SKILL.md` `description`을 보강 → 다시 복사 → 재검증.

> [!info] 산출물 위치 메모(v0.2 후보)
> 기본 출력은 스킬 폴더 내부(`${CLAUDE_SKILL_DIR}/output/`)다. 테스트 중에는 `--out-dir`로 테스트 프로젝트 루트나 Obsidian vault 클리핑 폴더를 지정하면 확인이 편하다. 설치본 안에 사용자 데이터가 쌓이지 않도록 기본 출력 경로 분리는 v0.2에서 정리.

---

## 4. (선택) 배포 — 비공개 GitHub 마켓플레이스 "한 줄 설치"

테스트가 끝나 검증되면 재사용용으로 배포한다. 스킬 루트에 `.claude-plugin/plugin.json`:

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
  "name": "youngbai-skills",
  "owner": { "name": "Youngbai" },
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

비공개 GitHub push 후, 다른 환경에서:

```text
/plugin marketplace add <github-user>/<repo>
/plugin install real-chrome-crawler@youngbai-skills
```

설치처에서 `uv sync` 1회 필요(런타임 의존성).

---

## 완료 기준 (DoD)

- [ ] H1 중복 제거 패치 적용, `.md`에 제목 1회만 출력
- [ ] 개발 폴더 루트에 `SKILL.md` 작성 완료
- [ ] **별도 테스트 프로젝트** `rcc-test/.claude/skills/real-chrome-crawler/`에 소스만 복사 + `uv sync`
- [ ] 테스트 프로젝트에서 Claude Code 시작 → `/real-chrome-crawler` 노출
- [ ] 자연어 프롬프트로 자동 발동 → `output/`에 `.md`/`.json` 생성
- [ ] 개발 폴더는 설치 테스트로 오염되지 않음(분리 유지)
- [ ] `ruff check` / `mypy` 전체 통과

---

## 결과 회신 양식

> [!todo] 실행 후 아래 표를 채워 회신해 주세요

| 항목 | 결과 | 비고 |
|------|------|------|
| 0) H1 중복 제거 | 예 / 아니오 | |
| 1) SKILL.md 작성 | 완료 | |
| 2) 테스트 프로젝트에 소스만 복사 + uv sync | 완료 / 실패 | 제외 정상 여부 |
| 3) `/real-chrome-crawler` 직접 호출 | 발동 / 미발동 | |
| 3) 자연어 자동 발동 | 발동 / 미발동 | 발동한 프롬프트 |
| 3) output md/json 생성 | 예 / 아니오 | |
| 4) 배포 설정(선택) | 적용 / 생략 | |
| ruff / mypy | | |
| 기타 오류/경고 | | |

---

> [!success] 회신 후
> STEP-05까지 통과하면 **v0.1 스킬 완성**입니다. v0.2 백로그: macOS/Linux 분기(RD-9 stub 해소), 기본 출력 경로 분리, OQ-3(페이지네이션/크롤 깊이)·OQ-5(인증 콘텐츠 범위) 확정, `references/selectors.md` 사이트별 규칙 축적, 더 강한 본문 추출 엔진(trafilatura 등) 어댑터화.
