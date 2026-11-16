r"""Hand-check helper: the codes and laws this repository dates by their day of enactment ("no commencement day read" in
the commit message), and what each one's own commencement sentence says ("вступает в силу ..."), in classes.
    python -X utf8 enactment_check.py <scripts dir> [out.csv] [reason regex]
The third argument picks other commits by the reason their message gives (e.g. "In force from \S+: on publication")."""
import collections, csv, json, re, subprocess, sys
from pathlib import Path

S = Path(sys.argv[1])
pin = json.load(open(S / "pins.json", encoding="utf-8"))["corpora"][0]
git = S / "sources" / "corpus" / (pin["repo"] + ".git")
paths = json.loads(subprocess.run(["git", "show", f"{pin['sha']}:data/paths.json"], cwd=git, capture_output=True).stdout)["paths"]


def g(*a):
    return subprocess.run(["git", *a], cwd=git, capture_output=True).stdout.decode("utf-8", "replace")


COMM = re.compile(r"(?i)(?:настоящий|данный)\s+(?:конституционный\s+)?(?:закон|кодекс)[^.]{0,200}?вступа\w+\s+в\s+силу[^.]{0,250}")


def cls(s):
    if not s:
        return "no commencement sentence found"
    if re.search(r"по истечении \w+ (?:дней|месяцев|месяца|дня) со дня (?:его )?официального опубликования", s):
        return "N days after publication"
    if re.search(r"по истечении \w+ (?:дней|месяцев|месяца) со дня (?:его )?подписания", s):
        return "N months after signing"
    if re.search(r"(?:со дня|с момента|с даты) (?:его )?официально[гй]о опубликования", s):
        return "on publication"
    if re.search(r"первого числа месяца, следующего за месяцем официального опубликования", s):
        return "first day of the month after publication"
    if re.search(r"(?:со дня|с момента|с даты) (?:его )?подписания", s):
        return "on signing"
    if re.search(r"со дня вступления в силу", s):
        return "with a treaty or another act"
    if re.search(r"с \d{1,2} \w+ \d{4}", s):
        return "a named day"
    return "other"


out = []
for rec in g("log", "--format=%H%x1f%an%x1f%B%x1e", pin["sha"]).split("\x1e"):
    if "\x1f" not in rec:
        continue
    h, an, body = rec.strip("\n").split("\x1f", 2)
    if not re.search(sys.argv[3] if len(sys.argv) > 3 else r"day of enactment \(no\s+commencement day read\)", body):
        continue
    tr = {k: v for k, v in re.findall(r"(?m)^(Enacted|Published|In-force): (\S+)", body)}
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
    out.append({"law": an, "folder": folder, "enacted": tr.get("Enacted", ""), "published": tr.get("Published", ""),
                "in_force": tr.get("In-force", ""), "class": cls(sent), "sentence": sent[:300], "commit": h})
w = csv.DictWriter(open(sys.argv[2] if len(sys.argv) > 2 else "enactment_check.csv", "w", encoding="utf-8", newline=""), fieldnames=list(out[0]))
w.writeheader(); w.writerows(out)
print(len(out), "acts dated by their day of enactment")
for k, n in collections.Counter(o["class"] for o in out).most_common():
    pub_after = sum(1 for o in out if o["class"] == k and o["published"] > o["in_force"])
    print(f"  {n:4d} {k}  (published after that day: {pub_after})")
