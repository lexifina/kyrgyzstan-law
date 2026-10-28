# How this history was made, and how to make it again

This file records exactly how the repository was built: the source, the commands, the software, the decisions made
by hand, and what an AI model did and did not do. The build writes it, so it describes the build that made this
commit.

## Short version

```sh
git clone https://github.com/lexifina/kyrgyzstan-law && cd kyrgyzstan-law
python -X utf8 tools/build.py --repo ../rebuilt --today 2026-10-28
git -C ../rebuilt rev-parse main        # the same hash as this repository's main
python -X utf8 tools/check_repo.py --repo ../rebuilt --no-record
python -X utf8 tools/test_repo.py --repo ../rebuilt --no-record
```

`tools/build.py` needs Python 3.12 or later (standard library only) and git. It reads the database (or its own cache,
`.cache/` beside it) and writes this repository into `--repo`. With the same API answers and the same `--today` it
gives the same commits with the same hashes. `data/editions.json` lists every edition with the sha256 of the API's
answer. `--offline` refuses to touch the network and fails on anything not cached.

## Source

All legal text and all information about changes come from the **Централизованный банк данных правовой информации
Министерства юстиции Кыргызской Республики** (cbd.minjust.gov.kg), through the open JSON API its web application
uses, `https://cbd.minjust.gov.kg/api/v1`. Nothing was typed in, summarised or rewritten. The build made
35 distinct requests.

| What | Where |
| --- | --- |
| An act's editions, with the day of each, and its references | `GetDocument?DocumentCode=N` (`editions`, `documentReferences`) |
| The text of an edition (Russian) | `GetEdition?editionId=N&lang=ru` (`contentRu`, Word-exported HTML) |
| An amending law's text, kind, number, adoption and publication | `GetDocument` and `GetEdition` of the law |

| Act | Document | Editions | Edition days |
| --- | --- | ---: | --- |
| Конституция 1993 | <https://cbd.minjust.gov.kg/1> | 9 | 1993-05-05 to 2010-06-27 |
| Конституция 2021 | <https://cbd.minjust.gov.kg/112213> | 1 | 2021-05-05 to 2021-05-05 |

The data was retrieved on 2026-10-28, at most 4 requests at a time and
0.3 s between the starts of two, with the user agent `lexifina-watch/1.0 (+https://lexifina.com/watch; corpus@lexifina.com)`. robots.txt has an empty Disallow and no Crawl-delay.
No terms of use or licence were found for the database or its API; see LICENSE. The repository is private.

## The build, step by step

1. `python -X utf8 scripts/kyrgyzstan-law/build.py` in Lexifina's own repository fetched the API answers and wrote
   this repository; every later build ran with `--offline`. `tools/build.py` here is the same file as
   `scripts/kyrgyzstan-law/build.py` there (git blob `755c6a8dd8d9aa61996cb34b0be0254de2f4cc18`), with `tools/reproduce.py`, which writes this file,
   `tools/check_repo.py` and `tools/test_repo.py`. The documentation commit is dated 2026-10-28, the day the data was
   retrieved (the newest file in the cache), not the day of the run.
2. `python -X utf8 scripts/kyrgyzstan-law/check_repo.py` read every edition back from git with `tools/v_sile_na.py`'s
   own lookup, on the day it took effect, and compared it with the edition's text:
   `9 editions checked (913 files compared byte for byte), 0 mismatches; 9 editions checked word for word against the whole edition text, 0 mismatches` (against history tip `302b38c7262b824a3817920049c50cdef2df8191`).
   File by file, the act's files on that day must be exactly the files the parser makes from that edition (for the
   2021 Constitution, on the day its last deferred part took effect). Word for word, the whole act printed in file
   order, without its markdown marks, must have the same words in the same order as the edition's HTML read with
   only its tags removed (hyphens, which the parser may join at line ends, are ignored by this comparison; the
   database's "УТРАТИЛА СИЛУ" banner over a past edition is not part of the act).
3. `python -X utf8 scripts/kyrgyzstan-law/build.py --offline --verify-rebuild` built the repository again from the cache into an empty temporary folder and compared every commit and tag: identical = `true` for 14 history commits and 22 tags (history tip `302b38c7262b824a3817920049c50cdef2df8191`). This documentation commit records that result, so the same command run on this build compares `main` itself too.
4. `python -X utf8 scripts/kyrgyzstan-law/test_repo.py` ran the functional smoke test against the built repository
   (standard library only):

   - PASS: git blame names Law No. 112 of 2001 in Art. 5 of the 1993 Constitution, and Law No. 59 of 2021 for part 2 of Art. 44 of the 2021 Constitution
   - PASS: v_sile_na: Art. 5 of the 1993 Constitution gains Russian as an official language on 2001-12-24; the 1996 edition applies from 1996-02-17, the day Law No. 1 was published
   - PASS: v_sile_na: the 2021 Constitution is in force from 2021-05-05, and part 2 of Art. 44 from 2023-01-01
   - PASS: v_sile_na: the 1993 Constitution is in force on 2010-07-01 and not from 2010-07-02
   - PASS: git log --follow on Art. 5 of the 1993 Constitution lists its laws in in-force order, from 1993 to its end
   - PASS: every tag resolves to a commit, and each day tag points at a commit in force that day
   - PASS: every history commit has In-force and Evidence trailers that git interpret-trailers parses
   - PASS: no commit is authored by Lexifina except the documentation commit; every committer is Lexifina
   - PASS: every history commit is dated noon in Bishkek on its In-force day (UTC+5/+6)
   - PASS: every command in the README table runs and prints a result

   10 of 10 passed (against history tip `302b38c7262b824a3817920049c50cdef2df8191`).

5. `git push origin main --tags` published it to GitHub as a private repository.

It ran with Python 3.12.10 and git version 2.46.0.windows.1 on Windows 11. No network service other than the database is involved.

## How the text and the commits are derived

Everything below is done by `tools/build.py`, deterministically.

- **Texts.** Every edition the database lists for each act, in Russian, an official language of the Kyrgyz
  Republic (the state language is Kyrgyz; the database has both).
- **Paragraphs.** Editions up to 2007 are fixed-width text, one HTML element per printed line; a paragraph begins at
  an indented line or after a blank line, and a line at the margin continues it. A word broken by a hyphen at the end
  of a printed line is joined again: without the hyphen when the joined word is printed whole elsewhere in the record,
  with it when the hyphenated word is; failing both, the hyphen is kept after a stem in "о"/"е" between two long parts
  (a compound such as "учебно-воспитательных"), and dropped otherwise. Line-end breaks in this build: .
  Runs of spaces are collapsed. Nothing else is changed.
- **Files.** One file per article, `<act>/statya-NNN.md`, with the chapter and section headings that begin with it
  (`##`) and the article heading (`#`); `uvod.md` is the title, the database's header (the edition's "В редакции ..."
  note is printed there), the table of contents and the preamble; `zaver.md` the closing words and signature.
- **Changes.** Consecutive editions are compared article by article.
- **Cause.** Each edition's header names its amending law by day and number, resolved to the law's document by the
  link in the text, the act's reference list or the database's search. A changed article is credited to that law when
  the article's own note names it, when the law's text names the article ("Статью 46 изложить..."), or when the law
  restates the whole Constitution ("О новой редакции Конституции"). A change nothing names is **not** credited: it is a
  commit by the publisher, `Kind: unexplained`, with the edition's law in `Edition-law:`. In this record they are the
  database's corrections of spelling and punctuation:

- konstitutsiya-1993 1996-02-17: statya-008, statya-031, statya-032, statya-044, statya-082, statya-085, zaver
- konstitutsiya-1993 1998-10-23: statya-032, statya-042, statya-052
- konstitutsiya-1993 2001-12-24: statya-065, statya-082, statya-085

- **Dates.** Each law's in-force day is read from its own words, quoted in the commit's `Evidence:` trailer:
  "со дня (его) официального опубликования" is the day of publication the law cites ("Эркин-Тоо" of that day) or,
  failing that, the database's publication day; "со дня подписания" the day of the law; an explicit day is that day.

| Act | Law | In force | Rule |
| --- | --- | --- | --- |
| Конституция 1993 | Конституция КР от 5 мая 1993 года (<https://cbd.minjust.gov.kg/1>) | - | no commencement sentence found |
| Конституция 1993 | Закон КР от 5 мая 1993 года № 1186-XII (<https://cbd.minjust.gov.kg/2>) | - | rule not recognised |
| Конституция 1993 | Закон КР от 16 февраля 1996 года № 1 (<https://cbd.minjust.gov.kg/608>) | 1996-02-17 | day of publication (the law cites 1996-02-17; the database gives 1996-01-27) |
| Конституция 1993 | Закон КР от 21 октября 1998 года № 134 (<https://cbd.minjust.gov.kg/141>) | 1998-10-23 | day of publication |
| Конституция 1993 | Закон КР от 24 декабря 2001 года № 112 (<https://cbd.minjust.gov.kg/944>) | - | day of publication |
| Конституция 1993 | Закон КР от 18 февраля 2003 года № 40 (<https://cbd.minjust.gov.kg/1164>) | 2003-02-19 | day of publication |
| Конституция 1993 | Закон КР от 9 ноября 2006 года № 180 (<https://cbd.minjust.gov.kg/500>) | 2006-11-09 | day of signature |
| Конституция 1993 | Закон КР от 15 января 2007 года № 2 (<https://cbd.minjust.gov.kg/4-3482>) | 2007-01-16 | day of publication |
| Конституция 1993 | Закон КР от 23 октября 2007 года № 157 (<https://cbd.minjust.gov.kg/202191>) | 2007-10-24 | day of publication |
| Конституция 1993 | Закон КР от 27 июня 2010 года (<https://cbd.minjust.gov.kg/202914>) | 2010-07-02 | day of publication of document 19400 (Постановление КР от 1 июля 2010 года № 130), 2010-07-02 |
| Конституция 1993 | Постановление КР от 1 июля 2010 года № 130 (<https://cbd.minjust.gov.kg/19400>) | - | no commencement sentence found |
| Конституция 2021 | Конституция КР от 5 мая 2021 года (<https://cbd.minjust.gov.kg/112213>) | - | no commencement sentence found |
| Конституция 2021 | Закон КР от 5 мая 2021 года № 59 (<https://cbd.minjust.gov.kg/112215>) | 2021-05-05 | day of publication |

- **Commits.** 2 for each act's first text, 7 by amending laws, 1 for a part
  that took effect later, 3 unexplained by the publisher and 1 for the 1993
  Constitution's replacement, in the order they took effect, then one for this documentation dated 2026-10-28.
  - The author is the law, as the database names it (`Закон КР от 16 февраля 1996 года № 1`), at an address that
    cannot exist (`doc-608@cbd-minjust.invalid`, the database's document number), so `git blame` names the law. The
    first texts are by the Constitution itself. Unexplained commits are by `ЦБД ПИ Минюста КР <cbd@minjust.invalid>`.
    Only the documentation commit is by Lexifina.
  - Author and committer dates are noon in Bishkek on the in-force day. The offsets are written into the builder
    (no time-zone database is used), from the tz database's Asia/Bishkek: UTC+6 with Soviet summer time to
    31 March 1991; UTC+5 from 31 August 1991, with summer time (UTC+6) from the first Sunday on or after 7 April to the
    last Sunday of September in 1992-1996 and from the last Sunday of March to the last Sunday of October in
    1997-2004 (in 2005 from 27 March); UTC+6 all year since 12 August 2005. No commit is before 1970.
  - Trailers: `In-force:` (every commit), `Enacted:`, `Published:`, `Evidence:`, `Kind:`, `Issuer:`, `Affecting:`,
    `Source:` (the law's document), `Consolidated:` (the edition), `Date-note:` where the database's own entry-into-force
    field differs, `Edition-law:` on unexplained commits.
  - Tags: each act's days (`konstitutsiya-1993/1996-02-17`) and each law (`zakon/1996-02-16-n1`); 22 in all.

## Decisions made by hand

These choices were made when the tool was written, after looking at the data. They are in the code.

1. **The acts.** The Constitution of 5 May 1993 (document 1) in all nine editions the database publishes, from the
   text put into effect on 5 May 1993 to its replacement by the Constitution of 27 June 2010, and the Constitution of
   5 May 2021 (document 112213), which the database publishes in one edition. The 2010 Constitution and the electoral
   law, which an earlier attempt began, are not in the record.
2. **The first days.** Neither Constitution states its own entry into force. The 1993 text took effect with Law
   No. 1186-XII of 5 May 1993 "О введении в действие Конституции" (document 2), which "вступает в силу одновременно с
   Конституцией" and repeals the 1978 Constitution "с 5 мая 1993 года": 1993-05-05. The 2021 text is the new wording
   set by Law No. 59 of 5 May 2021 (document 112215), whose Article 7 says "Настоящий Закон и Конституция в редакции
   настоящего Закона вступают в силу со дня официального опубликования"; the database gives 5 May 2021 (Эркин-Тоо
   No. 41) as its publication. Its Article 2 puts part 2 of Article 44 into effect on 1 January 2023, so that part is
   added by its own commit on that day.
3. **The 2010 replacement.** Overrides by document:

- document 202914: Закон принят референдумом и вступает в силу со дня официального опубликования итогов референдума; итоги (постановление ЦИК от 1 июля 2010 года № 130) опубликованы 2 июля 2010 года.

   The database's last edition of the 1993 Constitution (27.06.2010) reprints the previous text under its "УТРАТИЛА
   СИЛУ" note; the record removes the act's files on 2010-07-02 instead.
4. **Law No. 112 of 24 December 2001** (Article 5, languages) "вступает в силу с момента опубликования", but the
   database gives no publication for it. Its commit is dated the edition day, 24 December 2001, the day of the law,
   with `Evidence: date only`.
5. **The 2003 edition** is printed under a note that it lost force under the law of 9 November 2006; that note is not
   part of the text.
6. **Russian is the text of the record**; it is an official language, and the database's Russian and Kyrgyz texts are
   both official publications.

## What an AI model did

This repository was built on 2026-10-28 in **Claude Code**, Anthropic's coding tool, by the model **Claude Opus 5.5**
(model id `claude-opus-5-5`), working from a brief set at Lexifina: a private git history of Kyrgyz law to the
standard of Lexifina's other law records. An earlier session of the same model began the builder.

The model:

- **Researched the source:** the database's API, robots.txt and the absence of published terms.
- **Wrote all the code and text in this repository:** `tools/build.py`, `tools/reproduce.py`, `tools/check_repo.py`,
  `tools/test_repo.py`, `tools/v_sile_na.py`, the README, this file and the licence notice, and chose the design
  described in them.
- **Ran the commands above** and checked the results.

The model did **not**:

- **Write or edit any legal text.** Every word of every article, every date and every law's name is copied by the
  script from the database. The commit messages around them are fixed templates in the script.
- **Take part in building the history.** No AI model is called when the history is built or checked.

The work was not reviewed line by line by a lawyer. Only the official publications are authoritative; the database's
consolidated texts, and so this repository, are not.

## Prior art

Checked 2026-10-28: the legalize-dev organisation (github.com/legalize-dev) has no Kyrgyzstan repository; none of its code
or data is used. No other git history of Kyrgyz law was found.
