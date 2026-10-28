"""Functional smoke test of the built Kyrgyz law repository. Standard library only.

    python -X utf8 scripts/kyrgyzstan-law/test_repo.py [--repo ../kyrgyzstan-law] [--no-record]

It clones the repository into a temporary folder (so nothing in --repo is touched) and asserts that:
- `git blame` on a changed provision names the amending law as author;
- tools/v_sile_na.py gives the right text before and after known amendments, a part that takes effect later, and the
  end of the 1993 Constitution;
- `git log --follow` on an article lists the amending laws in date order;
- every tag resolves to a commit, and every history commit has an `In-force:` trailer that git parses;
- no commit is authored by Lexifina except the documentation commit;
- every git or python command in the README's table of questions runs without error.
The result is written to verification.json next to this script (unless --no-record), for REPRODUCE.md.
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EMAIL = 'kyrgyzstan-law@lexifina.com'


def run(cwd, *args, check=True) -> str:
    out = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, encoding='utf-8')
    if check and out.returncode:
        raise AssertionError(f'{" ".join(args)} failed: {out.stderr.strip()}')
    return out.stdout


def tests(repo: str) -> list[tuple[str, callable]]:
    py = sys.executable
    on = lambda day, act, art=None: run(repo, py, 'tools/v_sile_na.py', day, act, *([art] if art else []))
    out = []

    def blame():
        lines = run(repo, 'git', 'blame', '--line-porcelain', 'konstitutsiya-1993/2001-12-24', '--',
                    'konstitutsiya-1993/statya-005.md').split('\n')
        authors = [l[len('author '):] for l in lines if l.startswith('author ')]
        assert 'Закон КР от 24 декабря 2001 года № 112' in authors, authors
        assert 'Конституция КР от 5 мая 1993 года' in authors, authors
        lines = run(repo, 'git', 'blame', '--line-porcelain', 'konstitutsiya-2021/statya-044.md').split('\n')
        authors = [l[len('author '):] for l in lines if l.startswith('author ')]
        assert 'Закон КР от 5 мая 2021 года № 59' in authors and 'Конституция КР от 5 мая 2021 года' in authors, authors
    out.append(('git blame names Law No. 112 of 2001 in Art. 5 of the 1993 Constitution, and Law No. 59 of 2021 for part 2 of Art. 44 of the 2021 Constitution', blame))

    def on_date_1993():
        before, after = on('2001-12-23', 'konstitutsiya-1993', '5'), on('2001-12-24', 'konstitutsiya-1993', '5')
        assert 'в качестве официального языка' not in before, before
        assert 'в качестве официального языка употребляется русский язык' in after, after
        a, b = on('1996-02-16', 'konstitutsiya-1993'), on('1996-02-17', 'konstitutsiya-1993')
        assert '16 февраля 1996 года' not in a.split('## ')[0] and '16 февраля 1996 года' in b.split('## ')[0]
    out.append(('v_sile_na: Art. 5 of the 1993 Constitution gains Russian as an official language on 2001-12-24; the 1996 edition applies from 1996-02-17, the day Law No. 1 was published', on_date_1993))

    def deferred():
        a, b = on('2022-12-31', 'konstitutsiya-2021', '44'), on('2023-01-01', 'konstitutsiya-2021', '44')
        assert '\n2. Пенсия' not in a and '\n3. Государство' in a, a
        assert '\n2. Пенсия, социальное пособие' in b, b
        assert '# Статья 1\n' in on('2021-05-05', 'konstitutsiya-2021', '1')
        gone = subprocess.run([py, 'tools/v_sile_na.py', '2021-05-04', 'konstitutsiya-2021'], cwd=repo,
                              capture_output=True, text=True, encoding='utf-8')
        assert gone.returncode and 'not in the record' in gone.stderr, gone
    out.append(('v_sile_na: the 2021 Constitution is in force from 2021-05-05, and part 2 of Art. 44 from 2023-01-01', deferred))

    def end():
        assert '# Статья 46' in on('2010-07-01', 'konstitutsiya-1993', '46')
        gone = subprocess.run([py, 'tools/v_sile_na.py', '2010-07-02', 'konstitutsiya-1993'], cwd=repo,
                              capture_output=True, text=True, encoding='utf-8')
        assert gone.returncode and 'not in force' in gone.stderr, gone
    out.append(('v_sile_na: the 1993 Constitution is in force on 2010-07-01 and not from 2010-07-02', end))

    def follow():
        log = run(repo, 'git', 'log', '--follow', '--reverse',
                  '--format=%an%x09%(trailers:key=In-force,valueonly,separator=)', '--', 'konstitutsiya-1993/statya-005.md')
        rows = [l.split('\t') for l in log.strip().split('\n')]
        days = [d for _, d in rows]
        assert days == sorted(days) and len(days) >= 4, days
        laws = [a for a, _ in rows]
        assert laws[0] == 'Конституция КР от 5 мая 1993 года' and laws[-1] == 'Закон КР от 27 июня 2010 года', laws
        assert 'Закон КР от 24 декабря 2001 года № 112' in laws, laws
    out.append(('git log --follow on Art. 5 of the 1993 Constitution lists its laws in in-force order, from 1993 to its end', follow))

    def tags():
        names = run(repo, 'git', 'tag').split()
        assert len(names) > 10, names
        for t in names:
            run(repo, 'git', 'rev-parse', '--verify', '-q', f'{t}^{{commit}}')
            m = re.fullmatch(r'(konstitutsiya-\d{4})/(\d{4}-\d{2}-\d{2})', t)
            if m:
                body = run(repo, 'git', 'log', '-1', '--format=%B', t)
                assert f'In-force: {m.group(2)}' in body, t
    out.append(('every tag resolves to a commit, and each day tag points at a commit in force that day', tags))

    def trailers():
        hashes = run(repo, 'git', 'log', '--format=%H', 'main').split()
        for h in hashes[1:]:
            msg = run(repo, 'git', 'log', '-1', '--format=%B', h)
            parsed = subprocess.run(['git', 'interpret-trailers', '--parse'], cwd=repo, input=msg, capture_output=True,
                                    text=True, encoding='utf-8').stdout
            assert re.search(r'^In-force: \d{4}-\d{2}-\d{2}$', parsed, re.M), (h, parsed)
            assert re.search(r'^Evidence: ', parsed, re.M), (h, parsed)
        doc = run(repo, 'git', 'log', '-1', '--format=%s', hashes[0])
        assert doc.startswith('Документация'), doc
    out.append(('every history commit has In-force and Evidence trailers that git interpret-trailers parses', trailers))

    def authors():
        rows = run(repo, 'git', 'log', '--format=%H%x09%an%x09%ae%x09%cn%x09%ce', 'main').strip().split('\n')
        lex = [r for r in rows if r.split('\t')[2] == EMAIL]
        assert len(lex) == 1 and lex[0] == rows[0], lex
        assert all(r.split('\t')[3:] == ['Lexifina', EMAIL] for r in rows)
        assert all(r.split('\t')[2].endswith('.invalid') for r in rows[1:])
    out.append(('no commit is authored by Lexifina except the documentation commit; every committer is Lexifina', authors))

    def noon():
        rows = run(repo, 'git', 'log', '--format=%ad%x09%(trailers:key=In-force,valueonly,separator=)',
                   '--date=iso-strict', 'main').strip().split('\n')
        for r in rows[1:]:
            ad, day = r.split('\t')
            assert ad[:10] == day and ad[11:19] == '12:00:00', r
            off = ad[19:]
            assert off in ('+05:00', '+06:00') and (day < '2005-08-12' or off == '+06:00'), r
    out.append(('every history commit is dated noon in Bishkek on its In-force day (UTC+5/+6)', noon))

    def readme():
        text = (Path(repo) / 'README.md').read_text(encoding='utf-8')
        cmds = [c for c in re.findall(r'\| `([^`]+)` \|', text) if c.startswith(('git ', 'python '))]
        assert len(cmds) >= 10, cmds
        for c in cmds:
            args = shlex.split(c)
            if args[0] == 'python':
                args[0] = py
            if args[:2] == ['git', 'checkout']:
                args += ['-q']
            res = subprocess.run(args, cwd=repo, capture_output=True, text=True, encoding='utf-8')
            assert res.returncode == 0 and (res.stdout.strip() or args[:2] == ['git', 'checkout']), (c, res.stderr)
        run(repo, 'git', 'checkout', '-q', 'main')
    out.append(('every command in the README table runs and prints a result', readme))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=str(ROOT.parent / 'kyrgyzstan-law'))
    ap.add_argument('--no-record', action='store_true')
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    head = run(args.repo, 'git', 'rev-parse', 'main~1').strip()   # the history tip: stable across documentation rebuilds
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        clone = str(Path(tmp) / 'clone')
        run(tmp, 'git', 'clone', '-q', '--no-hardlinks', str(Path(args.repo).resolve()), clone)
        run(clone, 'git', 'fetch', '-q', '--force', '--tags')
        for name, fn in tests(clone):
            try:
                fn()
                ok = True
            except AssertionError as e:
                ok = False
                print(f'   {e}'[:600])
            print(f'{"PASS" if ok else "FAIL"}: {name}')
            results.append([name, ok])
        for f in Path(tmp).rglob('*'):
            os.chmod(f, 0o700)
    print(f'{sum(ok for _, ok in results)} of {len(results)} passed against {head}')
    if not args.no_record:
        p = HERE / 'verification.json'
        rec = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
        rec['smoke'] = {'results': results, 'head': head}
        p.write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    raise SystemExit(0 if all(ok for _, ok in results) else 1)


if __name__ == '__main__':
    main()
