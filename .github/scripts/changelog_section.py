"""Print the CHANGELOG.md section for a version, for use as release notes.

Usage: python changelog_section.py <version> [changelog_path]
Exits 1 if the changelog has no "## [<version>]" heading.
"""

import re
import sys


def changelog_section(text: str, version: str) -> str | None:
    heading = re.compile(rf"^## \[{re.escape(version)}\]", re.MULTILINE)
    match = heading.search(text)
    if not match:
        return None
    body_start = text.index("\n", match.end()) + 1
    next_heading = re.compile(r"^## ", re.MULTILINE).search(text, body_start)
    end = next_heading.start() if next_heading else len(text)
    section = text[body_start:end].strip()
    # Drop a trailing horizontal rule that separates sections in the file.
    return re.sub(r"\n-{3,}$", "", section).strip()


def main() -> int:
    version = sys.argv[1]
    path = sys.argv[2] if len(sys.argv) > 2 else "CHANGELOG.md"
    with open(path, encoding="utf-8") as f:
        section = changelog_section(f.read(), version)
    if not section:
        print(f"No CHANGELOG section for {version}", file=sys.stderr)
        return 1
    print(section)
    return 0


if __name__ == "__main__":
    sys.exit(main())
