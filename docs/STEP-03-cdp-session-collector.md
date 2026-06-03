---
title: STEP-03 — cdp_session.py + collector.py
project: real-chrome-crawler
step: 3
status: ready
date: 2026-06-03
tags:
  - claude-code
  - step
  - playwright
  - cdp
  - collector
---

# STEP-03 — `cdp_session.py` + `collector.py`

> [!abstract] 목표
> STEP-02가 확보한 CDP 엔드포인트에 Playwright `connect_over_cdp`로 **attach**하고, **기존 로그인 컨텍스트를 재사용**해 페이지를 수집한다. `page.goto` 대기 전략과 (선택적) 지연 로딩 스크롤까지 포함.

> [!note] 전제 (Resolved Decisions)
> - **RD-8**: 우리가 연 page/탭만 닫고, **사용자 브라우저·컨텍스트는 절대 닫지 않는다.**
> - **RD-3**: 연결 = `chromium.connect_over_cdp("http://localhost:<port>")`
> - `playwright install`은 **여전히 불필요** — 실행 중인 실제 Chrome에 붙기 때문.

---

## 1. 구현: `scripts/cdp_session.py`

아래 내용으로 **전체 교체**.

```python
"""cdp_session.py — 실행 중인 디버그 Chrome에 connect_over_cdp로 attach.

RD-8: 우리가 만든 page만 닫고, 사용자 브라우저/컨텍스트는 유지한다.
attach 후 browser.contexts[0](기존 로그인 컨텍스트)를 재사용한다.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright


class CdpSession:
    """attach된 브라우저/컨텍스트 핸들. new_page로 연 탭을 추적·정리한다."""

    def __init__(self, browser: Browser, context: BrowserContext) -> None:
        self.browser = browser
        self.context = context
        self._pages: list[Page] = []

    def new_page(self) -> Page:
        page = self.context.new_page()
        self._pages.append(page)
        return page

    def cleanup(self) -> None:
        """우리가 연 탭만 닫는다. 브라우저/기존 컨텍스트는 건드리지 않는다."""
        for page in self._pages:
            try:
                page.close()
            except Exception:  # noqa: BLE001 - 정리 단계, 실패해도 무시
                pass
        self._pages.clear()


@contextmanager
def cdp_attach(cdp_http: str) -> Iterator[CdpSession]:
    """디버그 Chrome에 attach하는 컨텍스트 매니저.

    종료 시 우리가 연 탭만 닫고 Playwright 드라이버만 정리한다(Chrome 유지).
    """
    pw = sync_playwright().start()
    session: CdpSession | None = None
    try:
        browser = pw.chromium.connect_over_cdp(cdp_http)
        # 기존 로그인 컨텍스트 재사용 (없으면 새로 생성)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        session = CdpSession(browser, context)
        yield session
    finally:
        if session is not None:
            session.cleanup()
        # 브라우저는 닫지 않는다(RD-8). 드라이버만 정리.
        pw.stop()
```

---

## 2. 구현: `scripts/collector.py`

아래 내용으로 **전체 교체**.

```python
"""collector.py — page.goto + 대기 전략 + HTML 수집.

단일 URL을 이동해 본문 HTML과 메타데이터를 수집한다.
지연 로딩 대응을 위한 간단한 auto_scroll 옵션 포함.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

from playwright.sync_api import Page

from scripts.cdp_session import CdpSession

WaitUntil = Literal["commit", "domcontentloaded", "load", "networkidle"]


@dataclass
class PageResult:
    url: str
    final_url: str
    title: str
    status: int | None
    html: str
    fetched_at: float = field(default_factory=time.time)


def collect_page(
    session: CdpSession,
    url: str,
    wait_until: WaitUntil = "domcontentloaded",
    timeout_ms: int = 30_000,
    settle_ms: int = 800,
    auto_scroll: bool = False,
) -> PageResult:
    """단일 페이지 수집. 우리가 연 탭에서 수행한다."""
    page = session.new_page()
    response = page.goto(url, wait_until=wait_until, timeout=timeout_ms)
    if settle_ms:
        page.wait_for_timeout(settle_ms)
    if auto_scroll:
        _scroll_to_bottom(page)
    return PageResult(
        url=url,
        final_url=page.url,
        title=page.title(),
        status=response.status if response else None,
        html=page.content(),
    )


def _scroll_to_bottom(
    page: Page, max_steps: int = 30, pause_ms: int = 500
) -> None:
    """무한 스크롤/지연 로딩 대응(간단). 높이가 멈추면 종료."""
    prev_height = 0
    for _ in range(max_steps):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(pause_ms)
        height = int(page.evaluate("document.body.scrollHeight"))
        if height == prev_height:
            break
        prev_height = height


def main() -> int:
    import argparse
    import json

    from scripts.chrome_launcher import ensure_chrome

    parser = argparse.ArgumentParser(description="단일 URL 수집 스모크 테스트")
    parser.add_argument("url")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--auto-scroll", action="store_true")
    args = parser.parse_args()

    info = ensure_chrome(port=args.port)
    with cdp_attach_import()(info["cdp_http"]) as session:
        result = collect_page(session, args.url, auto_scroll=args.auto_scroll)

    print(
        json.dumps(
            {
                "final_url": result.final_url,
                "title": result.title,
                "status": result.status,
                "html_length": len(result.html),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cdp_attach_import():  # 지연 import로 순환 의존 방지
    from scripts.cdp_session import cdp_attach

    return cdp_attach


if __name__ == "__main__":
    raise SystemExit(main())
```

> [!tip] import 구조
> `collector`는 `cdp_session.CdpSession`을 타입으로만 직접 import하고, 실행용 `cdp_attach`는 `main()` 안에서 지연 import한다. 모듈 간 결합을 느슨하게 유지하기 위함이다.

---

## 테스트 절차 (PowerShell)

```powershell
# 1) 스모크 테스트 — 공개 페이지(example.com)
uv run python -m scripts.collector https://example.com
#   기대: status 200, title "Example Domain", html_length > 0
#   동작: 디버그 Chrome에 새 탭이 열렸다가 종료 후 닫힘(메인 창은 유지)

# 2) (선택) 지연 로딩 페이지에서 auto-scroll
uv run python -m scripts.collector https://example.com --auto-scroll

# 3) 로그인 컨텍스트 재사용 확인(선택)
#    STEP-02에서 전용 프로필에 로그인해 둔 사이트의 '로그인 후에만 보이는' URL을
#    넣어 title/상태로 로그인 유지가 반영되는지 확인

# 4) 품질 게이트
uv run ruff check scripts/cdp_session.py scripts/collector.py
uv run mypy scripts/cdp_session.py scripts/collector.py
```

---

## 완료 기준 (DoD)

- [ ] `collector https://example.com` 가 status 200 / title / html_length JSON 출력
- [ ] 수집 중 디버그 Chrome에 **새 탭이 열렸다가 종료 시 닫힘**, 메인 창은 유지(RD-8)
- [ ] `connect_over_cdp`가 기존 컨텍스트(`contexts[0]`)에 attach 성공
- [ ] `playwright install` 없이 동작(실제 Chrome 사용)
- [ ] `ruff check` / `mypy` 통과

---

## 결과 회신 양식

> [!todo] 실행 후 아래 표를 채워 회신해 주세요

| 항목 | 결과 | 비고 |
|------|------|------|
| 1) example.com — status | | 200 기대 |
| 1) title / html_length | | |
| 새 탭 열림→종료 시 닫힘 | 예 / 아니오 | 메인 창 유지 여부 |
| 2) auto-scroll 동작 | | (선택) |
| 3) 로그인 컨텍스트 재사용 | | (선택, 시도 시) |
| 4) ruff / mypy | | 오류 시 원문 |
| 기타 오류/경고 | | |

회신 주시면 검증 후 **STEP-04 (`extractor.py` + `guards.py` — Obsidian MD/JSON 정규화 & robots/rate-limit/allowlist)** instruction을 생성하겠습니다.
