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
            f"  chrome.exe --remote-debugging-port={port} "
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
    p.add_argument(
        "--attach", action="store_true", help="이미 떠 있는 디버그 Chrome에만 붙기"
    )
    p.add_argument("--profile-dir", default=None, help="전용 프로필 경로 재정의")
    p.add_argument(
        "--wait-login", action="store_true", help="최초 실행 시 로그인 대기(Enter)"
    )
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
