---
title: STEP-02 — chrome_launcher.py (핵심)
project: real-chrome-crawler
step: 2
status: ready
date: 2026-06-03
tags:
  - claude-code
  - step
  - chrome-launcher
  - cdp
---

# STEP-02 — `chrome_launcher.py` 구현 *(기술 핵심)*

> [!abstract] 목표
> 전용 **비표준 user-data-dir**로 진짜 `chrome.exe`를 `--remote-debugging-port`와 함께 실행하고, CDP 엔드포인트(`webSocketDebuggerUrl`)를 확보·반환하는 모듈을 구현한다. 이 스킬의 봇 차단 우회 가치가 집중되는 단계.

> [!note] 확정된 전제 (Resolved Decisions, 갱신)
> - **RD-4 (수정)**: 프로필 전략 = **전용 디버그 프로필(1회 로그인)**. 메인 프로필 복사 ❌ (Chrome 136+ App-Bound Encryption으로 쿠키 복호화 불가).
> - **RD-9**: 1순위 OS = **Windows** (macOS/Linux는 `NotImplementedError` stub → v0.2).
> - 영속 프로필 경로 = `%LOCALAPPDATA%\real-chrome-crawler\chrome-profile`
> - 기본 포트 = `9222`, `--attach` 모드 옵션 제공.

> [!warning] Chrome 136+ 정책 핵심
> `--remote-debugging-port`는 **기본 데이터 디렉터리에선 무시**되고, 반드시 **비표준 `--user-data-dir`** 와 함께 써야 동작한다. 우리 영속 프로필 경로가 바로 그 "비표준 디렉터리"다. 따라서 메인 프로필 로그인은 상속되지 않으며, 전용 프로필에 **최초 1회 직접 로그인**하면 이후 영속 유지된다.

---

## 구현: `scripts/chrome_launcher.py`

아래 내용으로 `scripts/chrome_launcher.py`를 **전체 교체**한다. (표준 라이브러리만 사용, 외부 의존성 없음)

```python
"""chrome_launcher.py — 전용 디버그 프로필로 실제 Chrome 실행 + CDP 엔드포인트 확보.

전략 (RD-4 수정안): 메인 프로필을 복사/사용하지 않는다.
영속적인 비표준 user-data-dir로 진짜 chrome.exe를 --remote-debugging-port와 함께 띄운다.
- 최초 1회: 열린 창에서 대상 사이트에 직접 로그인 → 이후 영속 유지
- Chrome 136+ 정책 호환 (비표준 user-data-dir 필수)
- 1순위 OS: Windows. macOS/Linux는 v0.2 stub.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_PORT = 9222
APP_NAME = "real-chrome-crawler"


def _windows_chrome_candidates() -> list[Path]:
    candidates: list[Path] = []
    for key in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base = os.environ.get(key)
        if base:
            candidates.append(
                Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"
            )
    return candidates


def find_chrome_executable() -> Path:
    """OS별 chrome 실행 파일 경로를 찾는다. (Windows 1순위; 그 외 v0.2 stub)"""
    if sys.platform.startswith("win"):
        for path in _windows_chrome_candidates():
            if path.exists():
                return path
        raise FileNotFoundError("chrome.exe를 표준 설치 경로에서 찾지 못했습니다.")
    raise NotImplementedError(
        f"현재 OS({sys.platform})는 v0.1 미지원입니다. Windows에서 실행하세요. (v0.2 예정)"
    )


def get_profile_dir(custom: str | None = None) -> Path:
    """전용 디버그 프로필 디렉터리(영속). 비표준 경로 → Chrome 136+ 호환."""
    if custom:
        return Path(custom).expanduser().resolve()
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / APP_NAME / "chrome-profile"


def is_endpoint_alive(port: int, timeout: float = 1.0) -> dict | None:
    """디버깅 포트가 응답하면 /json/version JSON을 반환, 아니면 None."""
    url = f"http://localhost:{port}/json/version"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None


def wait_for_endpoint(port: int, timeout: float = 30.0) -> dict:
    """엔드포인트가 살아날 때까지 폴링."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        info = is_endpoint_alive(port)
        if info:
            return info
        time.sleep(0.5)
    raise TimeoutError(f"{timeout}s 내에 디버깅 포트({port})가 응답하지 않았습니다.")


def launch_chrome(port: int, profile_dir: Path) -> subprocess.Popen:
    """비표준 user-data-dir + 디버깅 포트로 chrome 실행 (부모와 독립)."""
    chrome = find_chrome_executable()
    profile_dir.mkdir(parents=True, exist_ok=True)
    args = [
        str(chrome),
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(
            subprocess, "DETACHED_PROCESS", 0
        )
    return subprocess.Popen(args, creationflags=creationflags)  # noqa: S603


def ensure_chrome(
    port: int = DEFAULT_PORT,
    attach: bool = False,
    profile_dir: str | None = None,
    wait_login: bool = False,
) -> dict:
    """디버그 Chrome을 확보하고 CDP 정보를 반환한다.

    반환: {"cdp_http", "ws", "browser", "first_run"}
    """
    # 이미 떠 있으면 재사용 (idempotent)
    info = is_endpoint_alive(port)
    if info:
        return {
            "cdp_http": f"http://localhost:{port}",
            "ws": info.get("webSocketDebuggerUrl", ""),
            "browser": info.get("Browser", ""),
            "first_run": False,
        }

    if attach:
        raise ConnectionError(
            f"--attach 모드인데 포트 {port}에 디버그 Chrome이 없습니다.\n"
            f"먼저 다음으로 실행하세요:\n"
            f'  chrome.exe --remote-debugging-port={port} '
            f'--user-data-dir="<비표준 경로>"'
        )

    pdir = get_profile_dir(profile_dir)
    first_run = not (pdir / "Local State").exists()
    launch_chrome(port, pdir)
    info = wait_for_endpoint(port)

    if first_run:
        print(
            "\n[안내] 전용 디버그 프로필을 새로 만들었습니다.\n"
            "열린 Chrome 창에서 수집 대상 사이트에 직접 로그인하세요.\n"
            "이 프로필은 영속 저장되어 다음 실행부터 로그인이 유지됩니다.\n"
        )
        if wait_login:
            input("로그인을 마쳤으면 Enter를 누르세요... ")

    return {
        "cdp_http": f"http://localhost:{port}",
        "ws": info.get("webSocketDebuggerUrl", ""),
        "browser": info.get("Browser", ""),
        "first_run": first_run,
    }


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="전용 디버그 프로필로 실제 Chrome 실행 + CDP 확보"
    )
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--attach", action="store_true", help="이미 떠 있는 디버그 Chrome에만 붙기")
    p.add_argument("--profile-dir", default=None, help="전용 프로필 경로 재정의")
    p.add_argument("--wait-login", action="store_true", help="최초 실행 시 로그인 대기(Enter)")
    return p


def main() -> int:
    args = _build_parser().parse_args()
    try:
        result = ensure_chrome(
            port=args.port,
            attach=args.attach,
            profile_dir=args.profile_dir,
            wait_login=args.wait_login,
        )
    except (FileNotFoundError, NotImplementedError, TimeoutError, ConnectionError) as e:
        print(f"[오류] {e}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

## 테스트 절차 (PowerShell)

```powershell
# 1) 최초 실행: 새 Chrome 창이 뜨고 JSON이 출력되어야 함 (first_run: true)
uv run python -m scripts.chrome_launcher --port 9222

# 2) 엔드포인트 수동 확인: 아래 URL을 아무 브라우저에서 열어 webSocketDebuggerUrl 확인
#    http://localhost:9222/json/version

# 3) 재실행: 기존 인스턴스 재사용 → 창 추가로 안 열리고 first_run: false
uv run python -m scripts.chrome_launcher --port 9222

# 4) attach 모드 오류 확인: 포트가 비어 있을 때(위 Chrome 닫고) 명확한 안내 메시지
#    (먼저 9222 Chrome 창을 닫은 뒤 실행)
uv run python -m scripts.chrome_launcher --attach --port 9222

# 5) 품질 게이트
uv run ruff check scripts/chrome_launcher.py
uv run mypy scripts/chrome_launcher.py
```

> [!tip] 핑거프린트 확인(선택)
> 1번 실행으로 열린 창에서 `https://bot.sannysoft.com` 에 접속해 webdriver 등 자동화 시그널이 **노출되지 않는지** 눈으로 확인하면 좋다. (진짜 chrome.exe이므로 깨끗해야 정상)

---

## 완료 기준 (DoD)

- [ ] 최초 실행 시 새 Chrome 창이 열리고, `cdp_http / ws / browser / first_run` JSON 출력
- [ ] `http://localhost:9222/json/version` 이 `webSocketDebuggerUrl` 반환
- [ ] 재실행 시 동일 인스턴스 재사용(`first_run: false`, 창 추가 없음)
- [ ] 전용 프로필이 `%LOCALAPPDATA%\real-chrome-crawler\chrome-profile` 에 생성됨
- [ ] `--attach` 모드에서 포트 부재 시 안내 메시지 출력 후 종료코드 1
- [ ] `ruff check` / `mypy` 통과

---

## 결과 회신 양식

> [!todo] 실행 후 아래 표를 채워 회신해 주세요

| 항목 | 결과 | 비고 |
|------|------|------|
| 1) 최초 실행 — 창 열림 & JSON | | `browser` 값(예: Chrome/14x...) 적어주세요 |
| `webSocketDebuggerUrl` 확보 | 예 / 아니오 | |
| 2) /json/version 수동 확인 | | |
| 3) 재실행 idempotent (`first_run:false`) | | 창 추가 여부 |
| 4) `--attach` 부재 시 안내 메시지 | | 메시지 원문 |
| 프로필 디렉터리 생성 경로 | | |
| 5) ruff / mypy | | 오류 시 원문 첨부 |
| 기타 오류/경고 | | |

회신 주시면 검증 후 **STEP-03 (`cdp_session.py` + `collector.py` — attach·페이지 수집)** instruction을 생성하겠습니다.
