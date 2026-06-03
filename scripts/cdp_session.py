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
