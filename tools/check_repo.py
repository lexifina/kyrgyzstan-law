"""Checks the git repository against the official text: every edition of every act in the database, read back from git
with tools/v_sile_na.py's lookup on the day it took effect, must equal that edition's text.

    python -X utf8 scripts/kyrgyzstan-law/check_repo.py [--repo ../kyrgyzstan-law] [--no-record]

Two checks per edition, from the cached API answers (no network):
1. File by file: the act's files in git on that day are exactly the files the build's parser makes from that edition
   (same set of files, same bytes). An edition with a part that takes effect later (the 2021 Constitution, Art. 44,
   part 2) is checked on the day of its last part, and on its first day it must differ only by that part.
2. Word for word: the whole act printed in file order, with its markdown marks removed, has the same words and
   punctuation in the same order as the edition's HTML with only its tags removed: block elements become line breaks, a
   hyphen at the end of a line joins the two halves, and hyphens are otherwise ignored (the parser decides whether a
   broken word keeps its hyphen; this check confirms that no word is lost, added or moved). The database's "УТРАТИЛА
   СИЛУ" banner over a past edition is not part of the act and is removed first.
After an act's replacement, no file of it may remain. The result is written to verification.json next to this script
(unless --no-record), for REPRODUCE.md.
"""
import argparse
import html as htmllib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402

TOKEN = re.compile(r'\w+|[^\w\s|-]')


def official_words(content: str, banner: str) -> list[str]:
    body = content[content.find('<body'):] if '<body' in content else content
    body = re.sub(r'<(?:p|pre|tr|h\d|div|table|br)\b[^>]*>', '\n', body)
    text = htmllib.unescape(re.sub(r'<[^>]+>', '', body)).replace('\u00a0', ' ').replace('\u00ad', '')
    text = re.sub(r'-[ \t]*\n[\s]*', '', text)
    words = TOKEN.findall(text.replace('-', ''))
    ban = TOKEN.findall(banner)
    if ban:
        if words[:len(ban)] != ban:
            raise SystemExit(f'banner not at the start: {ban[:8]} / {words[:8]}')
        words = words[len(ban):]
    return words


def repo_words(text: str) -> list[str]:
    lines = [re.sub(r'^#+ ', '', l) for l in text.split('\n')]
    return TOKEN.findall(' '.join(lines).replace('-', ''))


def files_at(repo: str, commit: str, slug: str) -> dict[str, str]:
    """The act's files at a commit, read with one ls-tree and one cat-file --batch (not one git show per file)."""
    out = subprocess.run(['git', 'ls-tree', '-r', commit, f'{slug}/'], cwd=repo, capture_output=True,
                         text=True, encoding='utf-8').stdout.split('\n')
    blobs = []
    for line in out:
        if not line:
            continue
        info, f = line.split('\t', 1)
        if f.endswith('.md') and not f.endswith('/README.md'):
            blobs.append((f[len(slug) + 1:], info.split()[2]))
    if not blobs:
        return {}
    data = subprocess.run(['git', 'cat-file', '--batch'], cwd=repo, input=''.join(f'{sha}\n' for _, sha in blobs).encode(),
                          capture_output=True).stdout
    res, pos = {}, 0
    for name, _ in blobs:
        nl = data.index(b'\n', pos)
        size = int(data[pos:nl].split()[2])
        res[name] = data[nl + 1:nl + 1 + size].decode('utf-8')
        pos = nl + 1 + size + 1
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=str(build.ROOT.parent / 'kyrgyzstan-law'))
    ap.add_argument('--no-record', action='store_true')
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    sys.path.insert(0, str(Path(args.repo) / 'tools'))
    import v_sile_na as reader
    build.prepare(True)
    versions = files = bad = wbad = 0
    per_act = {}

    def at(day, slug):
        commit = reader.commit_on(day, slug, cwd=args.repo)
        return files_at(args.repo, commit, slug) if commit else {}

    for act in build.ACTS:
        b = build.build_act(act, True)
        slug = act['slug']
        for v in b['versions']:
            expected = {build.file_name(k): u['text'] for k, u in v['units'].items()}
            deferred = v.get('deferred') or []
            day = max([v['in_force']] + [d['day'] for d in deferred])
            got = at(day, slug)
            versions += 1
            per_act[slug] = per_act.get(slug, 0) + 1
            files += len(expected)
            if got != expected:
                bad += 1
                diff = sorted(set(got) ^ set(expected)) or [k for k in expected if got.get(k) != expected[k]]
                print(f'MISMATCH {slug} {v["day"]} (on {day}): {diff[:5]}')
            if deferred:
                first = at(v['in_force'], slug)
                want = dict(expected, **{build.file_name(d['key']): d['before']['text'] for d in deferred})
                if first != want:
                    bad += 1
                    print(f'MISMATCH {slug} {v["in_force"]}: the first day differs by more than the deferred parts')
            whole = '\n'.join(got[f] for f in sorted(got, key=reader.order))
            ow, rw = official_words(v['content'], v['banner']), repo_words(whole)
            if ow != rw:
                wbad += 1
                i = next((i for i, (x, y) in enumerate(zip(ow, rw)) if x != y), min(len(ow), len(rw)))
                print(f'WORDS {slug} {v["day"]}: official {len(ow)} vs repo {len(rw)} words; first difference at '
                      f'{i}: {" ".join(ow[max(0, i - 6):i + 6])!r} / {" ".join(rw[max(0, i - 6):i + 6])!r}')
        if b['end']:
            law = b['end']['version']['laws'][0]
            day = b['laws'][law]['in_force']['day']
            left = files_at(args.repo, reader.commit_on(day, slug, cwd=args.repo), slug)
            if left:
                bad += 1
                print(f'MISMATCH {slug}: {len(left)} files remain after its end on {day}')
    tip = subprocess.run(['git', 'rev-parse', 'main~1'], cwd=args.repo, capture_output=True, text=True).stdout.strip()
    print(f'{versions} editions checked ({files} files), {bad} mismatches; {versions} editions word for word, {wbad} mismatches')
    print('per act:', per_act)
    if not args.no_record:
        p = HERE / 'verification.json'
        rec = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
        rec['check'] = {'versions': versions, 'files': files, 'mismatches': bad, 'wordcheck': versions,
                        'word_mismatches': wbad, 'per_act': per_act, 'history_tip': tip}
        p.write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    raise SystemExit(1 if bad or wbad else 0)


if __name__ == '__main__':
    main()
