"""Write a PEP 503 package index of the usd-brep wheels in this repository's GitHub releases.

    gh api repos/<owner>/<repo>/releases --paginate --slurp | python3 cadler/simple-index.py <out dir>

Writes <out dir>/simple/index.html and <out dir>/simple/usd-brep/index.html. The wheels stay
release assets; the index only links to them, with the sha256 GitHub records for each asset, so
pip and uv verify what they download. Draft releases are left out.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path


def page(title: str, links: list[str]) -> str:
    body = "\n".join(links)
    return f'<!DOCTYPE html>\n<html>\n<head><meta name="pypi:repository-version" content="1.0"><title>{title}</title></head>\n<body>\n{body}\n</body>\n</html>\n'


def main() -> None:
    out = Path(sys.argv[1])
    # --slurp: one JSON array per page, in an array
    releases = [r for page_ in json.load(sys.stdin) for r in page_]
    links = []
    for release in releases:
        if release.get("draft"):
            continue
        for asset in release.get("assets", []):
            name = asset["name"]
            if not (name.startswith("usd_brep-") and name.endswith(".whl")):
                continue
            digest = asset.get("digest") or ""
            if not digest.startswith("sha256:"):
                sys.exit(f"{name}: GitHub reports no sha256 for it")
            url = asset["browser_download_url"]
            links.append(
                f'<a href="{html.escape(url)}#sha256={digest[7:]}" data-requires-python="&gt;=3.12,&lt;3.13">{html.escape(name)}</a><br>'
            )
    if not links:
        sys.exit("no usd-brep wheels in the releases")
    links.sort()
    (out / "simple/usd-brep").mkdir(parents=True, exist_ok=True)
    (out / "simple/index.html").write_text(page("Simple index", ['<a href="usd-brep/">usd-brep</a><br>']))
    (out / "simple/usd-brep/index.html").write_text(page("Links for usd-brep", links))
    (out / "index.html").write_text(
        page("usd-brep for cadler", ['<p>Package index of cadler\'s usd-brep wheels: <a href="simple/">simple/</a> '
             '(<a href="https://github.com/abstractFlo/usd-brep">source</a>)</p>'])
    )
    print(f"{len(links)} wheels in {out}/simple/usd-brep/")


if __name__ == "__main__":
    main()
