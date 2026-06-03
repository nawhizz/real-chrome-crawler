---
title: STEP-04 — extractor.py + guards.py
project: real-chrome-crawler
step: 4
status: ready
date: 2026-06-03
tags:
  - claude-code
  - step
  - extractor
  - guards
  - obsidian
---

# STEP-04 — `extractor.py` + `guards.py`

> [!abstract] 목표
> 수집 HTML을 **Obsidian 호환 Markdown(YAML frontmatter + 출처) + 구조화 JSON**으로 정규화하고(RD-6), **robots.txt / rate limit / 도메인 allowlist** 가드를 붙인다(RD-7, RD-10).

> [!note] 전제 (Resolved Decisions)
> - **RD-6**: 출력 = Obsidian MD + JSON 동시
> - **RD-7**: robots.txt 확인 / random delay / domain allowlist
> - **RD-10**: robots.txt 위반 = **경고 후 진행**(warn) 기본, `block`/`ignore` 옵션

---

## 0. 의존성 추가 & mypy 설정

```powershell
uv add beautifulsoup4 markdownify
```

`pyproject.toml` 끝에 mypy 오버라이드를 추가한다(외부 라이브러리 타입 스텁 부재 대응):

```toml
[[tool.mypy.overrides]]
module = ["markdownify", "bs4"]
ignore_missing_imports = true
```

---

## 1. 구현: `scripts/guards.py`

아래 내용으로 **전체 교체**.

```python
"""guards.py — robots.txt 확인 / rate limit / 도메인 allowlist.

RD-10: robots.txt 위반은 기본 'warn'(경고 후 진행). 설정으로 block/ignore 가능.
"""

from __future__ import annotations

import random
import time
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlparse

RobotsPolicy = Literal["warn", "block", "ignore"]
DEFAULT_UA = "real-chrome-crawler"


@dataclass
class GuardReport:
    url: str
    host: str
    robots_allowed: bool | None  # None = 확인 불가
    robots_policy: RobotsPolicy
    allowlist_ok: bool
    blocked: bool
    warnings: list[str] = field(default_factory=list)


def check_domain_allowlist(host: str, allowlist: set[str]) -> bool:
    """allowlist가 비어 있으면 모두 허용. 있으면 포함 여부로 판정."""
    return True if not allowlist else host in allowlist


def check_robots(
    url: str, user_agent: str = DEFAULT_UA, timeout: float = 5.0
) -> bool | None:
    """robots.txt 기준 수집 가능 여부. 확인 불가 시 None."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    try:
        with urllib.request.urlopen(robots_url, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="replace")
        rp.parse(raw.splitlines())
    except (urllib.error.URLError, OSError):
        return None
    return rp.can_fetch(user_agent, url)


def evaluate(
    url: str,
    *,
    allowlist: set[str] | None = None,
    robots_policy: RobotsPolicy = "warn",
    user_agent: str = DEFAULT_UA,
) -> GuardReport:
    """수집 전 가드 평가. blocked=True면 호출측이 중단해야 한다."""
    host = urlparse(url).netloc
    warnings: list[str] = []
    blocked = False

    allow_ok = check_domain_allowlist(host, allowlist or set())
    if not allow_ok:
        blocked = True
        warnings.append(f"도메인 allowlist에 없음: {host}")

    robots_allowed: bool | None = None
    if robots_policy != "ignore":
        robots_allowed = check_robots(url, user_agent)
        if robots_allowed is False:
            if robots_policy == "block":
                blocked = True
                warnings.append(f"robots.txt 불허: {url} (정책=block → 중단)")
            else:
                warnings.append(f"robots.txt 불허: {url} (정책=warn → 경고 후 진행)")
        elif robots_allowed is None:
            warnings.append("robots.txt 확인 불가(없음/타임아웃) — 진행")

    return GuardReport(
        url=url,
        host=host,
        robots_allowed=robots_allowed,
        robots_policy=robots_policy,
        allowlist_ok=allow_ok,
        blocked=blocked,
        warnings=warnings,
    )


def polite_delay(min_s: float = 1.0, max_s: float = 3.0) -> None:
    """과도한 요청 방지용 랜덤 지연."""
    time.sleep(random.uniform(min_s, max_s))  # noqa: S311 - 보안용 아님
```

---

## 2. 구현: `scripts/extractor.py`

아래 내용으로 **전체 교체**.

```python
"""extractor.py — 수집 HTML → Obsidian 호환 Markdown + 구조화 JSON.

노이즈 태그 제거 → markdownify 변환 → YAML frontmatter + 출처 부착.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from scripts.collector import PageResult

NOISE_TAGS = [
    "script", "style", "noscript", "nav", "footer",
    "header", "aside", "form", "svg",
]


def html_to_markdown(html: str) -> str:
    """노이즈 제거 후 본문을 Markdown으로 변환."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    body = soup.body or soup
    markdown = md(str(body), heading_style="ATX")
    return re.sub(r"\n{3,}", "\n\n", markdown).strip()


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\-]+", "-", text.strip().lower())
    return re.sub(r"-{2,}", "-", slug).strip("-")[:60] or "page"


def to_obsidian_note(
    result: PageResult, body_md: str, tags: list[str] | None = None
) -> str:
    """YAML frontmatter + 출처 + 본문으로 Obsidian 노트를 만든다."""
    tags = tags or ["clipped"]
    fetched = datetime.fromtimestamp(
        result.fetched_at, tz=timezone.utc
    ).strftime("%Y-%m-%d")
    safe_title = result.title.replace('"', "'")
    fm_tags = "\n".join(f"  - {t}" for t in tags)
    frontmatter = (
        "---\n"
        f'title: "{safe_title}"\n'
        f"source: {result.final_url}\n"
        f"fetched: {fetched}\n"
        f"status: {result.status}\n"
        "tags:\n"
        f"{fm_tags}\n"
        "---\n"
    )
    return (
        f"{frontmatter}\n# {result.title}\n\n"
        f"출처: <{result.final_url}>\n\n{body_md}\n"
    )


def save_outputs(
    result: PageResult,
    body_md: str,
    out_dir: str = "output",
    tags: list[str] | None = None,
    include_html: bool = False,
) -> dict[str, str]:
    """Markdown + JSON 동시 저장. 반환: 저장 경로 dict."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.fromtimestamp(
        result.fetched_at, tz=timezone.utc
    ).strftime("%Y%m%d-%H%M%S")
    stem = f"{_slugify(result.title)}-{ts}"
    md_path = out / f"{stem}.md"
    json_path = out / f"{stem}.json"

    md_path.write_text(
        to_obsidian_note(result, body_md, tags), encoding="utf-8"
    )

    payload = asdict(result)
    if not include_html:
        payload.pop("html", None)
    payload["markdown_chars"] = len(body_md)
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"markdown": str(md_path), "json": str(json_path)}


def main() -> int:
    import argparse

    from scripts.cdp_session import cdp_attach
    from scripts.chrome_launcher import ensure_chrome
    from scripts.collector import collect_page
    from scripts.guards import evaluate, polite_delay

    parser = argparse.ArgumentParser(description="수집→정규화 엔드투엔드")
    parser.add_argument("url")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--out-dir", default="output")
    parser.add_argument("--auto-scroll", action="store_true")
    parser.add_argument(
        "--robots-policy", choices=["warn", "block", "ignore"], default="warn"
    )
    args = parser.parse_args()

    report = evaluate(args.url, robots_policy=args.robots_policy)
    for w in report.warnings:
        print(f"[guard] {w}")
    if report.blocked:
        print("[guard] 차단되어 수집을 중단합니다.")
        return 2

    polite_delay()
    info = ensure_chrome(port=args.port)
    with cdp_attach(info["cdp_http"]) as session:
        result = collect_page(session, args.url, auto_scroll=args.auto_scroll)

    body_md = html_to_markdown(result.html)
    paths = save_outputs(result, body_md, out_dir=args.out_dir)
    print(json.dumps(paths, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

## 테스트 절차 (PowerShell)

```powershell
# 1) 엔드투엔드 — example.com 수집→정규화→저장
uv run python -m scripts.extractor https://example.com
#   기대: [guard] robots 관련 메시지 → output\<slug>.md / .json 경로 출력

# 2) 산출물 확인
type output\*.md       # frontmatter(title/source/fetched/status/tags) + 본문
type output\*.json     # 구조화 필드(+ markdown_chars), html 제외 확인

# 3) robots 정책 플러밍 확인(선택)
uv run python -m scripts.extractor https://example.com --robots-policy ignore
#   → robots 메시지 없이 진행

# 4) 품질 게이트
uv run ruff check scripts/guards.py scripts/extractor.py
uv run mypy scripts/guards.py scripts/extractor.py
```

> [!info] 출력 형식
> Markdown은 외부 URL을 `[text](url)` / `<url>` 형식으로 유지하므로 Obsidian에서 그대로 렌더된다. 표는 markdownify가 GFM 표로 변환한다.

---

## 완료 기준 (DoD)

- [ ] `output\*.md` 에 YAML frontmatter(title/source/fetched/status/tags) + 본문 존재
- [ ] `output\*.json` 에 구조화 필드 + `markdown_chars` 존재, `html` 미포함(기본)
- [ ] `[guard]` 로그가 robots/지연 동작을 표시하고, warn 기본은 진행됨
- [ ] `--robots-policy ignore` 시 robots 확인 생략
- [ ] `ruff check` / `mypy` 통과(오버라이드 적용)

---

## 결과 회신 양식

> [!todo] 실행 후 아래 표를 채워 회신해 주세요

| 항목 | 결과 | 비고 |
|------|------|------|
| 1) extractor 실행 — 저장 경로 출력 | | md/json 경로 |
| 2) MD frontmatter 정상 | 예 / 아니오 | title/source/fetched/status/tags |
| 2) JSON 구조 + html 제외 | 예 / 아니오 | markdown_chars 포함 여부 |
| guard 로그 메시지 | | robots 관련 원문 |
| 3) `--robots-policy ignore` | | (선택) |
| 4) ruff / mypy | | 오류 시 원문 |
| 기타 오류/경고 | | |

회신 주시면 검증 후 **STEP-05 (`SKILL.md` 작성 + 테스트 프롬프트 + `.skill` 패키징)** — 마지막 단계 instruction을 생성하겠습니다.
