"""Counts the places in the law texts where "до", "по" or "не позднее" comes before a past date, month or year, which of
them the time-limit search (ingest/textscan.py limits()) reads, and the forms of those it misses (the numbers in the
READMEs).
    python -X utf8 measure_missed.py <scripts dir>      (reads sources/corpus/<repo>.git at the pinned commit)"""
import collections, json, re, subprocess, sys
from pathlib import Path

S = Path(sys.argv[1])
sys.path.insert(0, str(S / "ingest"))
import textscan as t  # noqa: E402

t._LANG["v"] = "ru"
pin = json.load(open(S / "pins.json", encoding="utf-8"))["corpora"][0]
git = S / "sources" / "corpus" / (pin["repo"] + ".git")
NOT_LAW = ("data/", "tools/", "README", "REPRODUCE", "LICENSE", "corpus.json", "zakony.csv")
MON = r"(?:январ|феврал|март|апрел|ма[яй]|июн|июл|август|сентябр|октябр|ноябр|декабр)\w*"
W = r"(?<![\w-])(?:до|по|не позднее)\s+"
FORMS = [  # (name, pattern); the year is the last group
    ("a day, month and year", re.compile(rf"(?i){W}(?:«|\")?\d{{1,2}}(?:-?го)?(?:»|\")?\s+{MON}\s+((?:18|19|20)\d\d)")),
    ("a date in figures", re.compile(rf"(?i){W}\d{{1,2}}\.\d{{1,2}}\.((?:18|19|20)\d\d)")),
    ("a month and year, no day", re.compile(rf"(?i){W}{MON}\s+((?:18|19|20)\d\d)")),
    ("the end of a year (до конца/окончания)", re.compile(rf"(?i){W}(?:конца|окончания)\s+(?:\w+\s+){{0,2}}?((?:18|19|20)\d\d)")),
    ("a bare year with года/г.", re.compile(rf"(?i){W}((?:18|19|20)\d\d)\s*(?:года|году|г\.)")),
]
out = subprocess.run(["git", "grep", "-I", "-n", "-i", "-P", r"(?<![\w-])(до|по|не позднее)\s", pin["sha"], "--", "*.md"],
                     cwd=git, capture_output=True).stdout.decode("utf-8", "replace")
read, missed = collections.Counter(), collections.Counter()
examples = collections.defaultdict(list)
for line in out.splitlines():
    _, path, _, text = line.split(":", 3)
    if path.startswith(NOT_LAW) or path.rsplit("/", 1)[-1] == "README.md":
        continue
    found = [(d, c) for d, c in t.limits(text) if d < "2026-11-16"]
    for name, rx in FORMS:
        for m in rx.finditer(text):
            if int(m.group(1)) >= 2026:
                continue
            core = re.sub(r"\s+", " ", m.group(0))
            if any(core in c for _, c in found):
                read[name] += 1
            else:
                missed[name] += 1
                if len(examples[name]) < 3:
                    examples[name].append(f"{path}: {core}")
print("read:", dict(read), "total", sum(read.values()))
print("missed:", sum(missed.values()))
for f, n in missed.most_common():
    print(f"  {n:5d} {f}")
    for e in examples[f]:
        print("        ", e[:160])
