"""Reproduce the completed coarse-network numerical study without external downloads.
Run from anywhere: python run_all.py
Use --checks-only for the small numerical/property test suite.
Existing result CSVs are regenerated. The supplied PDF/HTML remain unchanged.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checks-only', action='store_true', help='Run 26 core checks only.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    (root / 'results').mkdir(exist_ok=True)
    commands = [[sys.executable, str(root/'code'/'test_model.py')]]
    if not args.checks_only:
        commands += [
            [sys.executable, str(root/'code'/'run_experiment.py'), '--output', str(root/'results')],
            [sys.executable, str(root/'code'/'paired_timing.py')],
            [sys.executable, str(root/'code'/'analyze.py')],
        ]
    for i, cmd in enumerate(commands, start=1):
        print(f'\n[{i}/{len(commands)}] {Path(cmd[1]).name}', flush=True)
        try:
            subprocess.run(cmd, cwd=root, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f'Execution stopped: {exc}', file=sys.stderr)
            return 1
    print('\nCompleted. Interpret outputs as report-derived coarse-model experiments, not mapped floods.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
