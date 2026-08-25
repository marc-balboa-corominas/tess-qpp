from pathlib import Path
import argparse
from build_phase3b_closure import validate_closure
if __name__ == "__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root", default=".")
    args=ap.parse_args(); validate_closure(Path(args.repo_root).resolve())
