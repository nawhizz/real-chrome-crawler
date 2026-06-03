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
