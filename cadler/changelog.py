"""cadler/CHANGELOG.md from the git history: what this fork changed in NVIDIA's usd-brep, per
version in cadler/version (1.0.1+cadler.N), newest first. A version holds the commits since the
version before it, up to its release tag (v1.0.1-cadler.N) or, before it is tagged, the last
commit with that version; NVIDIA's own commits (those in the tag v1.0.1 the version builds on)
are left out. Running it again fills in whatever is missing.

    python cadler/changelog.py               writes cadler/CHANGELOG.md for HEAD
    python cadler/changelog.py "<subject>"   the same, with the commit about to be made (its
                                             subject) under the version in cadler/version
"""

import datetime
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], check=True, capture_output=True, text=True).stdout.strip()


def has_ref(ref):
    return subprocess.run(["git", "-C", ROOT, "rev-parse", "--verify", "--quiet", ref], capture_output=True).returncode == 0


def versions():
    """(version, last commit) oldest first, from the commits that changed cadler/version."""
    found = {}
    for commit in git("log", "--reverse", "--format=%H", "--", "cadler/version").split("\n"):
        version = git("show", f"{commit}:cadler/version")
        found.setdefault(version, commit)
    ordered = []
    for version in found:
        tag = "v" + version.replace("+", "-")
        if has_ref(tag):
            end = tag
        else:
            # not released yet: up to the last commit that still has this version
            later = [v for v in found if list(found).index(v) > list(found).index(version)]
            end = f"{found[later[0]]}~1" if later else "HEAD"
        ordered.append((version, end))
    # the version the commit about to be made brings
    with open(os.path.join(ROOT, "cadler", "version"), encoding="utf-8") as file:
        current = file.read().strip()
    if current not in found:
        ordered.append((current, None))
    return ordered


def main(pending=None):
    sections = []
    previous = None
    all_versions = versions()
    for index, (version, end) in enumerate(all_versions):
        upstream = "v" + version.split("+")[0]
        excluded = [upstream] + ([previous] if previous else [])
        subjects = git("log", "--no-merges", "--format=%s", end, "--not", *excluded).split("\n") if end else []
        date = git("log", "-1", "--format=%cs", end) if end else datetime.date.today().isoformat()
        if pending and index == len(all_versions) - 1:
            subjects.insert(0, pending)
            date = datetime.date.today().isoformat()
        released = has_ref("v" + version.replace("+", "-"))
        title = f"## {version} - {date}" + ("" if released else " (not released yet)")
        lines = [f"- {subject}" for subject in subjects if subject]
        sections.append("\n".join([title, "", *lines]))
        previous = end
    text = "\n".join([
        "# Changelog of cadler's usd-brep",
        "",
        "What this fork changed in NVIDIA's usd-brep, per version in `cadler/version`, newest first;",
        "NVIDIA's own changes are in `CHANGELOG.md`. Written from the git history by",
        "`cadler/changelog.py`; do not edit it by hand.",
        "",
        *[section + "\n" for section in reversed(sections)],
    ])
    with open(os.path.join(ROOT, "cadler", "CHANGELOG.md"), "w", encoding="utf-8") as file:
        file.write(text)
    print(f"cadler/CHANGELOG.md: {len(sections)} versions, newest {all_versions[-1][0]}")


if __name__ == "__main__":
    main(sys.argv[1].strip() if len(sys.argv) > 1 else None)
