#!/usr/bin/env python3
"""Build and deploy the quiz site to GitHub Pages.

Regenerates docs/index.md from whatever quiz HTML files are in docs/quizzes/,
then runs `mkdocs gh-deploy` to build and push to the gh-pages branch.

Usage:
    python deploy.py              # regenerate index, build, deploy
    python deploy.py --build      # regenerate index and build only (no push)
    python deploy.py --index      # regenerate index only
    python deploy.py --serve      # regenerate index and serve locally
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QUIZ_DIR = ROOT / "docs" / "quizzes"
INDEX = ROOT / "docs" / "index.md"

# Filename convention: <subject>_<lesson>_<type>_<number>.html
# Lesson is optional (e.g. la_sentence_diagram_practice.html).
FILENAME_RE = re.compile(
    r"^(?P<subject>math|la|history)"
    r"(?:_(?P<lesson>\d+))?"
    r"_(?P<rest>.+)$"
)

SUBJECTS = [
    ("math", "Math"),
    ("la", "Language Arts"),
    ("history", "History"),
]

# Nicer labels for specific files, where the filename alone isn't descriptive.
# Key is the filename stem; anything not listed gets a label derived from the name.
LABEL_OVERRIDES = {
    "math_167_test_17": "Test 17 — Final Exam",
    "math_unit_conversions_practice": "Unit Conversion Drill",
    "la_169_test_17": "Test 17 — Final Exam",
    "la_154_test_15_diagrams": "Test 15 — Sentence Diagrams",
}

HEADER = """# Practice Quizzes

Interactive practice quizzes. Each one opens in your browser, checks your answers as
you go, and saves your progress on that device.

!!! tip "How to use these"
    Answers must be exact — including spelling, capitalization, and punctuation.
    Your work is saved automatically, so you can close the page and come back to it.
"""


def label_for(rest: str) -> str:
    """Turn the trailing part of a filename into a human-readable label."""
    words = rest.split("_")
    out = []
    for w in words:
        if w in ("quiz", "test"):
            out.append(w.capitalize())
        elif w.isdigit():
            out.append(w)
        else:
            out.append(w.capitalize())
    return " ".join(out)


def scan_quizzes():
    """Return {subject: [(sort_key, label, lesson, filename), ...]}."""
    if not QUIZ_DIR.is_dir():
        sys.exit(f"error: {QUIZ_DIR} does not exist")

    found = {key: [] for key, _ in SUBJECTS}
    unmatched = []

    for path in sorted(QUIZ_DIR.glob("*.html")):
        m = FILENAME_RE.match(path.stem)
        if not m:
            unmatched.append(path.name)
            continue
        subject = m.group("subject")
        lesson = m.group("lesson")
        label = LABEL_OVERRIDES.get(path.stem) or label_for(m.group("rest"))
        # Sort by lesson number; unnumbered entries sort last.
        sort_key = (int(lesson) if lesson else 10**6, label)
        found[subject].append((sort_key, label, lesson, path.name))

    for name in unmatched:
        print(f"  warning: skipping {name} (does not match naming convention)")

    for key in found:
        found[key].sort()
    return found


def build_index() -> str:
    found = scan_quizzes()
    parts = [HEADER]

    for key, heading in SUBJECTS:
        rows = found[key]
        if not rows:
            continue
        parts.append(f"\n## {heading}\n")
        parts.append("| Quiz | Lesson |")
        parts.append("| --- | --- |")
        for _, label, lesson, filename in rows:
            parts.append(f"| [{label}](quizzes/{filename}) | {lesson or '—'} |")
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def write_index() -> int:
    content = build_index()
    INDEX.write_text(content, encoding="utf-8")
    count = len(list(QUIZ_DIR.glob("*.html")))
    print(f"wrote {INDEX.relative_to(ROOT)} ({count} quiz files)")
    return count


def run(cmd):
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--index", action="store_true",
                       help="regenerate docs/index.md only")
    group.add_argument("--build", action="store_true",
                       help="regenerate index and build, but do not deploy")
    group.add_argument("--serve", action="store_true",
                       help="regenerate index and serve locally at localhost:8000")
    args = ap.parse_args()

    write_index()

    if args.index:
        return
    if args.serve:
        run([sys.executable, "-m", "mkdocs", "serve"])
        return
    if args.build:
        run([sys.executable, "-m", "mkdocs", "build", "--strict"])
        return

    run([sys.executable, "-m", "mkdocs", "build", "--strict"])
    run([sys.executable, "-m", "mkdocs", "gh-deploy", "--force"])
    print("\nDeployed. Site: https://mjredmond.github.io/school2/")
    print("Note: commit and push your source changes separately (deploy.py only "
          "pushes the built site to gh-pages).")


if __name__ == "__main__":
    main()
