"""Hand-check helper for the retroactive-date flags: for each flagged act, the day its commit gives (In-force), the days
in its trailers (Enacted, Published), the commit message's reason for the day, and the act's own commencement sentence
("вступает в силу ...") read from its files at the pin.
    python -X utf8 retro_check.py <scripts dir> [out.csv]"""
import csv, json, re, subprocess, sys
from pathlib import Path
import duckdb

S = Path(sys.argv[1])
pin = json.load(open(S / "pins.json", encoding="utf-8"))["corpora"][0]
git = S / "sources" / "corpus" / (pin["repo"] + ".git")
paths = json.loads(subprocess.run(["git", "show", f"{pin['sha']}:data/paths.json"], cwd=git, capture_output=True).stdout)["paths"]


def g(*a):
    return subprocess.run(["git", *a], cwd=git, capture_output=True).stdout.decode("utf-8", "replace")


rows = duckdb.sql(f"select law, in_force, made, back_days from '{(S / 'findings/run/ranked_retroactive_date.parquet').as_posix()}' order by back_days desc").fetchall()
log = g("log", "--format=%H%x1f%an%x1f%B%x1e", pin["sha"])
by_author = {}
for rec in log.split("\x1e"):
    if "\x1f" in rec:
        h, an, body = rec.strip("\n").split("\x1f", 2)
        by_author.setdefault(an, (h, body))
COMM = re.compile(r"(?i)(?:настоящий|данный)\s+(?:конституционный\s+)?(?:закон|кодекс)[^.]{0,200}?вступа\w+\s+в\s+силу[^.]{0,250}")
out = []
for law, inf, made, back in rows:
    h, body = by_author.get(law, ("", ""))
    reason = (re.search(r"In force from [0-9-]+: ([^\n]*)", body) or [None, ""])[1]
    files = [l for l in g("show", "--name-only", "--format=", h).splitlines() if l.endswith(".md")]
    folder = files[0].rsplit("/", 1)[0] if files else ""
    folder = paths.get(folder, folder)
    names = [l for l in g("ls-tree", "--name-only", pin["sha"], folder + "/").splitlines() if not l.endswith("README.md")]
    sent = ""
    for f in reversed(names):
        m = COMM.search(g("show", f"{pin['sha']}:{f}"))
        if m:
            sent = re.sub(r"\s+", " ", m.group(0))
            break
    kind = ("on publication" if re.search(r"со дня (?:его )?официального опубликования", sent) else
            "days after publication" if re.search(r"по истечении|через", sent) else
            "a date" if re.search(r"\d{4}", sent) else "other" if sent else "none read")
    out.append({"law": law, "in_force": inf, "published": str(made), "days": back, "folder": folder, "reason": reason,
                "own_text": kind, "sentence": sent[:300], "commit": h})
w = csv.DictWriter(open(sys.argv[2] if len(sys.argv) > 2 else "retro_check.csv", "w", encoding="utf-8", newline=""), fieldnames=list(out[0]))
w.writeheader(); w.writerows(out)
import collections
print(collections.Counter((o["reason"][:40], o["own_text"]) for o in out).most_common())
