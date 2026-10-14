#!/usr/bin/env python3
"""Build the CrewScore demo workspace into a directory you name.

One command, deterministic (byte-identical output every run), synthetic text only:

    python scripts/build_demo_workspace.py ./demo-workspace

The workspace carries the three cases a recording needs:

  routine         hardened-ops.md                    clears --threshold 50
  exception       ines-support-assistant.md          fails --require human_gate.approval_required
  needs approval  ines-support-assistant.md          `crewscore fix --plan` proposes; a person writes the sentence

and the hero edit: appending one sentence turns the required-control gate from
exit 2 to exit 0 (ines-support-assistant.approved.md holds the finished file).
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "examples" / "corpus" / "prompts"

CONTROL = "human_gate.approval_required"
SENTENCE = "A human must approve any refund or account change before it happens.\n"

README = f"""# CrewScore demo workspace (synthetic)

Built by `python scripts/build_demo_workspace.py <dir>`. Every file is invented text.

1. Routine: the hardened prompt clears the CI threshold.

       crewscore test -f hardened-ops.md --no-explain --threshold 50     # exit 0

2. Exception: a new prompt that never says a person approves anything.

       crewscore test -f ines-support-assistant.md --no-explain --require {CONTROL}   # exit 2

3. Needs approval: CrewScore proposes wording, writes nothing.

       crewscore fix --prompt-file ines-support-assistant.md --plan   # file not modified

4. Hero: add one sentence, run the same gate again.

       echo "{SENTENCE.strip()}" >> ines-support-assistant.md
       crewscore test -f ines-support-assistant.md --no-explain --require {CONTROL}   # exit 0

`ines-support-assistant.approved.md` is the finished file, for resetting between takes.
Coverage means the words are present, not that the assistant obeys them.
"""


def build(target: Path) -> dict[str, str]:
    """Write the workspace into ``target`` (created if needed). Returns name -> text."""
    target.mkdir(parents=True, exist_ok=True)
    bare = (CORPUS / "01-bare-assistant.md").read_text(encoding="utf-8")
    files = {
        "hardened-ops.md": (CORPUS / "05-hardened-ops.md").read_text(encoding="utf-8"),
        "ines-support-assistant.md": bare,
        "ines-support-assistant.approved.md": bare.rstrip("\n") + "\n" + SENTENCE,
        "README.md": README,
    }
    for name, text in files.items():
        (target / name).write_text(text, encoding="utf-8", newline="\n")
    return files


def _ascii(path: Path) -> str:
    """Console output must survive a cp1252 stdout on Windows."""
    return str(path).encode("ascii", "backslashreplace").decode("ascii")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("directory", type=Path, help="target directory")
    parser.add_argument("--force", action="store_true", help="replace a non-empty target")
    args = parser.parse_args(argv)
    target = args.directory.resolve()
    if target.exists() and any(target.iterdir()):
        if not args.force:
            print(f"{_ascii(target)} is not empty; pass --force to rebuild it.", file=sys.stderr)
            return 1
        cwd = Path.cwd().resolve()
        if target == cwd or target in cwd.parents:
            print("Refusing --force on the current directory or one of its parents.", file=sys.stderr)
            return 1
        shutil.rmtree(target)
    files = build(target)
    print(f"built {len(files)} files in {_ascii(target)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
