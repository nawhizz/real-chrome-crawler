"""extractor.py — 수집 HTML → Obsidian 호환 Markdown + 구조화 JSON.

노이즈 태그 제거 → markdownify 변환 → YAML frontmatter + 출처 부착.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

# Windows CP949 터미널에서 한/특수문자 출력 오류 방지
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from scripts.collector import PageResult

NOISE_TAGS = [
    "script",
    "style",
    "noscript",
    "nav",
    "footer",
    "header",
    "aside",
    "form",
    "svg",
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


def _strip_leading_h1(body: str, title: str) -> str:
    """본문 첫 H1이 제목과 동일하면 제거(중복 방지)."""
    match = re.match(r"\s*#\s+(.+?)\s*\n", body)
    if match and match.group(1).strip().lower() == title.strip().lower():
        return body[match.end() :].lstrip("\n")
    return body


def to_obsidian_note(
    result: PageResult, body_md: str, tags: list[str] | None = None
) -> str:
    """YAML frontmatter + 출처 + 본문으로 Obsidian 노트를 만든다."""
    tags = tags or ["clipped"]
    fetched = datetime.fromtimestamp(result.fetched_at, tz=timezone.utc).strftime(
        "%Y-%m-%d"
    )
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
    body = _strip_leading_h1(body_md, result.title)
    return (
        f"{frontmatter}\n# {result.title}\n\n" f"출처: <{result.final_url}>\n\n{body}\n"
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
    ts = datetime.fromtimestamp(result.fetched_at, tz=timezone.utc).strftime(
        "%Y%m%d-%H%M%S"
    )
    stem = f"{_slugify(result.title)}-{ts}"
    md_path = out / f"{stem}.md"
    json_path = out / f"{stem}.json"

    md_path.write_text(to_obsidian_note(result, body_md, tags), encoding="utf-8")

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
