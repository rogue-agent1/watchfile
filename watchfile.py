#!/usr/bin/env python3
"""watchfile - Watch files for changes and run a command.

One file. Zero deps. Like entr but simpler.

Usage:
  watchfile.py <pattern> -- <command...>
  watchfile.py "*.py" -- pytest
  watchfile.py src/ -- make build
  echo file.txt | watchfile.py -- cat file.txt
"""

import argparse
import fnmatch
import os
import subprocess
import sys
import time
from pathlib import Path


def find_files(patterns: list[str]) -> list[str]:
    """Resolve glob patterns to file paths."""
    files = []
    for pattern in patterns:
        p = Path(pattern)
        if p.is_file():
            files.append(str(p.resolve()))
        elif p.is_dir():
            for root, dirs, fnames in os.walk(str(p)):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for f in fnames:
                    files.append(os.path.join(root, f))
        else:
            # Glob pattern
            parent = p.parent if str(p.parent) != '.' else Path('.')
            for root, dirs, fnames in os.walk(str(parent)):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for f in fnames:
                    if fnmatch.fnmatch(f, p.name):
                        files.append(os.path.join(root, f))
    return sorted(set(files))


def get_mtimes(files: list[str]) -> dict[str, float]:
    """Get modification times for files."""
    mtimes = {}
    for f in files:
        try:
            mtimes[f] = os.path.getmtime(f)
        except OSError:
            pass
    return mtimes


def run_command(cmd: list[str]) -> int:
    """Run command, return exit code."""
    try:
        result = subprocess.run(cmd, shell=len(cmd) == 1)
        return result.returncode
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print(f"Error running command: {e}", file=sys.stderr)
        return 1


def main():
    # Split args on --
    argv = sys.argv[1:]
    if '--' not in argv:
        print("Usage: watchfile.py <patterns...> -- <command...>", file=sys.stderr)
        print("  watchfile.py '*.py' -- pytest", file=sys.stderr)
        print("  watchfile.py src/ -- make build", file=sys.stderr)
        return 1

    sep = argv.index('--')
    patterns = argv[:sep]
    cmd = argv[sep + 1:]

    if not cmd:
        print("Error: no command specified after --", file=sys.stderr)
        return 1

    # If no patterns, read from stdin
    if not patterns:
        if sys.stdin.isatty():
            print("Error: no files specified and stdin is a terminal", file=sys.stderr)
            return 1
        patterns = [line.strip() for line in sys.stdin if line.strip()]

    files = find_files(patterns)
    if not files:
        print(f"Error: no files match {patterns}", file=sys.stderr)
        return 1

    print(f"Watching {len(files)} files...", file=sys.stderr)
    interval = 0.5  # seconds

    prev_mtimes = get_mtimes(files)

    # Run once initially
    print(f"\n--- running: {' '.join(cmd)} ---", file=sys.stderr)
    run_command(cmd)

    try:
        while True:
            time.sleep(interval)
            # Re-scan for new files matching patterns
            current_files = find_files(patterns)
            current_mtimes = get_mtimes(current_files)

            changed = []
            for f, mtime in current_mtimes.items():
                if f not in prev_mtimes or prev_mtimes[f] != mtime:
                    changed.append(f)

            if changed:
                for f in changed:
                    rel = os.path.relpath(f)
                    print(f"  changed: {rel}", file=sys.stderr)
                print(f"\n--- running: {' '.join(cmd)} ---", file=sys.stderr)
                run_command(cmd)
                prev_mtimes = get_mtimes(current_files)
            else:
                prev_mtimes = current_mtimes

    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
