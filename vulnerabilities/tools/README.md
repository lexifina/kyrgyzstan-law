# Tools

The scripts behind this Kyrgyzstan-only run of global-law's vulnerability detectors. They run inside a copy of
[global-law/vulnerabilities/scripts](https://github.com/lexifina/global-law/tree/main/vulnerabilities/scripts) (Python 3.11+,
`pip install duckdb pyarrow`), with a bare clone of this repository at `sources/corpus/kyrgyzstan-law.git`, a blobless bare
clone of global-law at `sources/global-law.git`, and a `pins.json` that names only kyrgyzstan-law and its commit (language
`ru`). `build_vulns.py`, `flags_chart.py`, `late_ext_select.py`, `late_ext_rebut.py`, `patch_ru.py` and the hand-check helpers
sit two folders above the scripts, next to `config.json`.

| Script | What it does |
| --- | --- |
| `run.sh` | Indexes the history and texts, maps paths to the folders since the move (`map_moved.py`), adds this repository's history rows, and runs the detectors (`bash run.sh <shards>`) |
| `add_root.py` | Builds the history rows from this repository's own commits (global-law replays it only up to an earlier commit), so the history detectors read every change |
| `map_moved.py` | Rewrites the paths in the history table to each act's folder since the move of 10 November 2026 (`data/paths.json`), so that an act's history is not split in two at the move; `run.sh` runs it after the history is indexed |
| `patch_ru.py` | The Russian fixes below, in the copy of global-law's scripts (`python -X utf8 patch_ru.py <scripts dir>`; a fix already in place is skipped) |
| `run_triage.sh` | The model review: the 40 strongest flags per category, the 40 strongest lapsed time limits in law texts, and the empty periods |
| `late_ext_select.py` | Chooses the empty periods for global-law's review of that category (there were none here) |
| `late_ext_rebut.py` | Adds the second, arguing-against pass to the empty-period review, as `triage.py` does for the other categories |
| `build_vulns.py` | Builds `data/flags.csv`, `data/reviewed.csv` and `data/by_category.csv` from the findings and the model review |
| `flags_chart.py` | Draws the chart at the top of the READMEs, in Russian and English, light and dark |
| `config.json` | The repository, the Russian category names, the files that are not law, and the chart's labels |
| `patch_detectors.py` | Fixes blind spots found in runs on several country repositories in the copy of global-law's scripts (`python -X utf8 patch_detectors.py <scripts dir>`; a fix already in place is skipped) |
| `patch_detectors_vi.py`, `patch_es.py`, `patch_ca.py`, `patch_en.py`, `patch_de.py`, `patch_en_et.py`, `patch_co.py`, `patch_sv.py` | The same for the Vietnamese, Spanish, Catalan, English (two rounds), German, Colombian and Salvadoran blind spots found by other runs; this run's copy carries them all, and they change nothing here |
| `patch_pt.py`, `apply_patches.py` | The Brazilian Portuguese fixes, written after this run was set up and not applied to it, and the script that applies every patch above once, in order, recording each (`redo.py` runs it) |
| `redo.py` | Runs those patches, then again only the scans and detectors the fixes change, the model review of lapsed time limits, references to deleted provisions and empty periods, and the build (`python -X utf8 redo.py <run folder> [--keep-reviews] [--full]`; `--full` runs every step again through `run.sh`; `EMBED_FONTS` names the script that embeds the chart's fonts). It does not run `patch_ru.py`; run that first |
| `measure_missed.py` | Counts the places in the law texts where "до", "по" or "не позднее" comes before a past date, month or year, which of them the time-limit search reads, and the forms of those it misses (the numbers in the READMEs) |
| `retro_check.py` | Hand-check helper: for each retroactive-date flag, the day the commit gives, its `Enacted` and `Published` trailers, the commit message's reason for the day, and the act's own sentence on its entry into force |
| `enactment_check.py` | Hand-check helper: the codes and laws dated by the date they bear ("no commencement day read"), or with a third argument by another reason in the commit message, grouped by what their own sentence on entry into force says (the numbers in "Problems found in this repository") |

The model review needs `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` and `LLM_AUTH` set for an OpenAI-compatible Responses API.
It was run as `bash run_triage.sh '^(data/|tools/|vulnerabilities/|README|REPRODUCE|LICENSE|corpus\.json|zakony\.csv)'`;
every law is under `act/`, `code/`, `konst-zakon/`, `konstitutsiya-1993/`, `zakon/` or a code's own folder
(`trudovoy-kodeks-kyrgyzskoy-respubliki/` and the like: codes that kept their folder at the move, as `data/paths.json` shows),
so the review of lapsed time limits in law texts drew the same 40 flags as the review of all of them, and `build_vulns.py`
keeps the later review of each flag.

The detectors in this copy already carry every fix of `patch_detectors.py` and the other patches above except
`patch_pt.py`. Changes made for this repository:

- `add_root.py` counts as law the kinds `Закон` and `Конституция`, which this repository gives to the commits of the
  Constitutions' history (9 and 2), beside `law` (the codes and laws never amended, 2,440) and `publisher` (the current text
  of the 498 amended ones), which the kit already counted: 2,949 commits. The 3 corrections the database made to the 1993
  Constitution with no law named (`Kind: unexplained`) and the documentation commits are left out.
- `patch_ru.py`, time limits: "не позднее" (not later than) before a date is now read, as the Bulgarian "не по-късно от"
  is; "до" and "по ... включительно" before a date with a Russian month name ("до 31 декабря 2020 года", "до 1 января
  2021 г.") or in figures ("до 31.12.2020") were already read. 11 lapsed time limits come from it.
- `patch_ru.py`, references: the article files here are `statya-012.md` and, for an inserted article, `statya-131-1.md`,
  which had no key, so the reference-based detectors (references to repealed placeholders, dead fines) saw no article at all;
  "статья 131-1" was read as article 131 (now 131-1, while "статьями 56-59" stays a range); only "статья" and "статьи" were
  read, not "статье", "статью", "статьей", "статьями", "статей" and the like; and "статьи 5 Закона ...", "статьей 12
  Налогового кодекса" (another act named after the number) were read as the act's own articles ("настоящего Закона" and
  "настоящего Кодекса" stay the act's own). The scan still reads a reference in an amending law ("абзац четвертый статьи 7
  изложить ...") as one to the amending law's own article when the amended law is named before it: the one flag in that
  category.
- `patch_ru.py`, references to repealed placeholders: `исключ[её]н\w*` (deleted, a repeal marker) also matched "за
  исключением" (except) and "исключения" (exclusion), so six of the first seven flags were articles that are in force; now
  only "исключен", "исключена", "исключено", "исключены" count.
- `config.json` counts the top-level files (`README.md`, `README.en.md`, `REPRODUCE.md`, `REPRODUCE-acts.md`, `LICENSE`,
  `corpus.json`, `zakony.csv`), `data/` and `tools/` as not law; each act's `README.md` (its title and list of articles) is
  not scanned, and its `preambula.md` is part of the act.
- `pins.json` already named the language (`ru`), and Russian month names in the genitive ("января" ... "декабря") were
  already in the time-limit search.
