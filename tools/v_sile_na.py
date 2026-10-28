"""Prints an act, or one article of it, as it stood on a given day, from this repository's history.

    python tools/v_sile_na.py 2000-01-01 konstitutsiya-1993 46     # Art. 46 of the 1993 Constitution on 1 January 2000
    python tools/v_sile_na.py 2024-01-01 konstitutsiya-2021        # the whole 2021 Constitution

The act is named by its folder. The article is its number ("46", "17-1"), or "uvod" (the title and opening words) /
"zaver" (the closing words). Every commit carries the day its text took effect in its "In-force:" trailer; the day is
read from the trailer, never from the commit date. Standard library only.
"""
import datetime as dt
import re
import subprocess
import sys


def git(*args: str, cwd=None) -> str:
    return subprocess.run(['git', *args], capture_output=True, text=True, encoding='utf-8', check=True, cwd=cwd).stdout


def commit_on(day: str, path: str, cwd=None, branch: str = 'main') -> str | None:
    """The last commit touching `path` whose In-force day is on or before `day` (history is linear and in order)."""
    out = git('log', '--format=%H%x00%(trailers:key=In-force,valueonly,separator=)%x01', branch, '--', path, cwd=cwd)
    for rec in out.split('\x01'):
        rec = rec.strip()
        if not rec:
            continue
        h, d = rec.split('\x00')
        if d.strip() and d.strip() <= day:
            return h
    return None


def order(name: str) -> tuple:
    key = name.rsplit('/', 1)[-1][:-3]
    if key == 'uvod':
        return (0, 0, 0)
    m = re.fullmatch(r'statya-(\d+)(?:-(\d+))?', key)
    if m:
        return (1, int(m.group(1)), int(m.group(2) or 0))
    if key == 'zaver':
        return (3, 0, 0)
    return (4, 0, 0)


def file_for(article: str) -> str:
    a = article.removesuffix('.md')
    if a in ('uvod', 'zaver') or a.startswith('statya-'):
        return f'{a}.md'
    m = re.fullmatch(r'(\d+)(?:-(\d+))?', a)
    if not m:
        sys.exit(f'unknown article {article!r}')
    return f'statya-{int(m.group(1)):03d}' + (f'-{int(m.group(2))}' if m.group(2) else '') + '.md'


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    day, act = sys.argv[1], sys.argv[2].strip('/')
    dt.date.fromisoformat(day)
    branch = 'budushchee' if day > dt.date.today().isoformat() and git('branch', '--list', 'budushchee').strip() else 'main'
    commit = commit_on(day, act, branch=branch)
    if not commit:
        sys.exit(f'{act} is not in the record on {day}.')
    files = [f for f in git('ls-tree', '-r', '--name-only', commit, f'{act}/').split('\n')
             if f.endswith('.md') and not f.endswith('/README.md')]
    if not files:
        sys.exit(f'{act} was not in force on {day}.')
    if len(sys.argv) > 3:
        name = file_for(sys.argv[3])
        try:
            print(git('show', f'{commit}:{act}/{name}'), end='')
        except subprocess.CalledProcessError:
            sys.exit(f'{act}/{name} was not in force on {day}.')
        return
    for f in sorted(files, key=order):
        print(git('show', f'{commit}:{f}'))


if __name__ == '__main__':
    main()
