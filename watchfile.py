#!/usr/bin/env python3
"""watchfile - file/directory watcher that detects changes and runs commands."""

import argparse, os, sys, time, subprocess, fnmatch, hashlib

def get_snapshot(paths, patterns, ignore, recursive):
    """Get {path: (mtime, size)} for matching files."""
    snap = {}
    for base in paths:
        if os.path.isfile(base):
            if matches(base, patterns, ignore):
                st = os.stat(base)
                snap[base] = (st.st_mtime, st.st_size)
            continue
        walker = os.walk(base) if recursive else [(base, [], os.listdir(base))]
        for root, dirs, files in walker:
            # Prune ignored dirs
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, p) for p in ignore)]
            for f in files:
                fp = os.path.join(root, f)
                if matches(fp, patterns, ignore):
                    try:
                        st = os.stat(fp)
                        snap[fp] = (st.st_mtime, st.st_size)
                    except OSError:
                        pass
    return snap

def matches(path, patterns, ignore):
    name = os.path.basename(path)
    if ignore and any(fnmatch.fnmatch(name, p) for p in ignore):
        return False
    if not patterns:
        return True
    return any(fnmatch.fnmatch(name, p) for p in patterns)

def diff_snapshots(old, new):
    added = set(new) - set(old)
    removed = set(old) - set(new)
    modified = {p for p in set(old) & set(new) if old[p] != new[p]}
    return added, removed, modified

def run_command(cmd, changed_files):
    env = {**os.environ, "CHANGED": " ".join(changed_files)}
    # Replace $FILE placeholder
    if "$FILE" in cmd:
        for f in changed_files:
            actual = cmd.replace("$FILE", f)
            subprocess.run(actual, shell=True, env=env)
    else:
        subprocess.run(cmd, shell=True, env=env)

def cmd_watch(args):
    paths = args.paths
    interval = args.interval
    patterns = args.pattern or []
    ignore = args.ignore or [".git", "__pycache__", "*.pyc", ".DS_Store", "node_modules"]
    cmd = args.run
    recursive = not args.no_recursive
    verbose = args.verbose

    print(f"  Watching: {', '.join(paths)}")
    if patterns:
        print(f"  Patterns: {', '.join(patterns)}")
    if cmd:
        print(f"  Command:  {cmd}")
    print(f"  Interval: {interval}s")
    print(f"  Press Ctrl+C to stop\n")

    prev = get_snapshot(paths, patterns, ignore, recursive)
    print(f"  Tracking {len(prev)} files")

    events = 0
    try:
        while True:
            time.sleep(interval)
            curr = get_snapshot(paths, patterns, ignore, recursive)
            added, removed, modified = diff_snapshots(prev, curr)

            if added or removed or modified:
                ts = time.strftime("%H:%M:%S")
                changed = list(added | modified)
                if added:
                    for f in sorted(added):
                        print(f"  [{ts}] + {f}")
                        events += 1
                if removed:
                    for f in sorted(removed):
                        print(f"  [{ts}] - {f}")
                        events += 1
                if modified:
                    for f in sorted(modified):
                        print(f"  [{ts}] ~ {f}")
                        events += 1
                if cmd and changed:
                    print(f"  [{ts}] Running: {cmd}")
                    run_command(cmd, changed)
                    print()

            prev = curr
    except KeyboardInterrupt:
        print(f"\n  Stopped. {events} events detected.\n")

def cmd_snapshot(args):
    """Take a snapshot and save/compare."""
    paths = args.paths
    patterns = args.pattern or []
    ignore = args.ignore or [".git", "__pycache__", "*.pyc", ".DS_Store", "node_modules"]
    recursive = not args.no_recursive

    snap = get_snapshot(paths, patterns, ignore, recursive)

    if args.save:
        import json
        data = {p: {"mtime": m, "size": s} for p, (m, s) in snap.items()}
        with open(args.save, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  Saved snapshot: {len(snap)} files → {args.save}")
        return

    if args.compare:
        import json
        with open(args.compare) as f:
            old_data = json.load(f)
        old = {p: (d["mtime"], d["size"]) for p, d in old_data.items()}
        added, removed, modified = diff_snapshots(old, snap)
        if not added and not removed and not modified:
            print("  No changes detected.")
        else:
            for f in sorted(added):
                print(f"  + {f}")
            for f in sorted(removed):
                print(f"  - {f}")
            for f in sorted(modified):
                print(f"  ~ {f}")
            print(f"\n  {len(added)} added, {len(removed)} removed, {len(modified)} modified")
        return

    # Just list
    for p in sorted(snap):
        m, s = snap[p]
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(m))
        print(f"  {ts}  {s:>8}  {p}")
    print(f"\n  {len(snap)} files")

def main():
    p = argparse.ArgumentParser(description="File watcher")
    sp = p.add_subparsers(dest="cmd")

    w = sp.add_parser("watch", help="Watch for changes")
    w.add_argument("paths", nargs="+", help="Files/dirs to watch")
    w.add_argument("-p", "--pattern", action="append", help="File patterns (e.g. *.py)")
    w.add_argument("-i", "--ignore", action="append", help="Ignore patterns")
    w.add_argument("-r", "--run", help="Command to run on change")
    w.add_argument("--interval", type=float, default=1.0)
    w.add_argument("--no-recursive", action="store_true")
    w.add_argument("-v", "--verbose", action="store_true")
    w.set_defaults(func=cmd_watch)

    s = sp.add_parser("snapshot", help="Take/compare snapshots")
    s.add_argument("paths", nargs="+")
    s.add_argument("-p", "--pattern", action="append")
    s.add_argument("-i", "--ignore", action="append")
    s.add_argument("--no-recursive", action="store_true")
    s.add_argument("--save", help="Save snapshot to file")
    s.add_argument("--compare", help="Compare with saved snapshot")
    s.set_defaults(func=cmd_snapshot)

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        sys.exit(1)
    args.func(args)

if __name__ == "__main__":
    main()
