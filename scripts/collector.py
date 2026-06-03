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


def _scroll_to_bottom(page: Page, max_steps: int = 30, pause_ms: int = 500) -> None:
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
