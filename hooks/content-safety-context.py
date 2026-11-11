import sys
from pathlib import Path

POLICY_PATH = Path(__file__).resolve().parents[1] / "rules" / "untrusted-content.md"


def main() -> int:
    try:
        rules = POLICY_PATH.read_text(encoding="utf-8")
    except OSError:
        rules = ""
    if not rules.strip():
        print("jc plugin: content-safety rules are unavailable.", file=sys.stderr)
        return 2
    print(rules, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
