# Kyrgyz law, change by change

The Constitutions of the Kyrgyz Republic as a git repository: the **Constitution of 5 May 1993** in all nine editions the
Ministry of Justice publishes, from 1993 until it was replaced by the Constitution of 27 June 2010, and the
**Constitution of 5 May 2021**. Each amending law is one commit, credited to that law and dated the day it took effect,
at noon in Bishkek. The text is the Russian text of the [Централизованный банк данных правовой информации
Министерства юстиции Кыргызской Республики](https://cbd.minjust.gov.kg).

*По-русски: [ниже](#по-русски).*

## A lawyer's questions as git commands

| Question | Command |
| --- | --- |
| What did Art. 46 of the 1993 Constitution say on 1 January 2000? | `python tools/v_sile_na.py 2000-01-01 konstitutsiya-1993 46` |
| Art. 5 (languages) before and after Law No. 112 of 2001 | `python tools/v_sile_na.py 2001-12-23 konstitutsiya-1993 5` |
| The whole 1993 Constitution on 1 January 1997 | `python tools/v_sile_na.py 1997-01-01 konstitutsiya-1993` |
| Art. 44 of the 2021 Constitution on 1 January 2023 | `python tools/v_sile_na.py 2023-01-01 konstitutsiya-2021 44` |
| Which law wrote each line of an article? | `git blame konstitutsiya-2021/statya-044.md` |
| The same for the 1993 Constitution, as it stood on a day | `git blame konstitutsiya-1993/2001-12-24 -- konstitutsiya-1993/statya-005.md` |
| Every change to an article, with the law behind it | `git log -p --follow -- konstitutsiya-1993/statya-005.md` |
| Everything one law changed | `git show --stat zakon/1996-02-16-n1` |
| Every law that changed the 1993 Constitution, in order | `git log --reverse --format='%(trailers:key=In-force,valueonly,separator=)%x09%an' -- konstitutsiya-1993` |
| The state of the Constitution on a day it changed | `git checkout konstitutsiya-1993/1998-10-23` |
| What no law explains | `git log --grep='^Kind: unexplained' --format='%h%x09%(trailers:key=In-force,valueonly,separator=)%x09%s'` |

The laws with their dates are in [`zakony.csv`](zakony.csv); each act's articles, with how often each changed, are in
its folder's `README.md`. After a rebuild of this repository, refresh old clones with `git fetch --force --tags`. For
`git rev-list --before`, give the end of the day (`--before="1998-10-23T23:59:59+06:00"`): commits are at noon.

## The dates, and which one we use

A Kyrgyz law is dated the day it is signed (`Enacted:`), published in the official newspaper "Эркин-Тоо"
(`Published:`), and takes effect on the day it says. **Commits are dated the day the law took effect, read from the
law's own words** ("вступает в силу со дня его официального опубликования", "со дня подписания"), which are quoted in
the commit's `Evidence:` trailer. The database dates its editions by the day of the amending law, often a day or two
earlier; the edition day is in the tag of the law, the in-force day in the tag of the act.

- The 1993 Constitution took effect on 5 May 1993 with the law that put it into effect; the 2021 Constitution on
  5 May 2021, the day Law No. 59 was published. Part 2 of Art. 44 of the 2021 Constitution took effect on
  1 January 2023 and is added by its own commit that day.
- The 1993 Constitution ends on 2 July 2010, when the Constitution adopted by the referendum of 27 June 2010 took
  effect (the referendum results were published that day). **The 2010 Constitution is not in this record**: between
  2 July 2010 and 5 May 2021 the tool prints nothing.
- Law No. 112 of 24 December 2001 took effect "с момента опубликования", but the database gives no publication day;
  its commit is dated the day of the law and says so (`Evidence: date only`).

Times are noon in Bishkek (UTC+5, with summer time UTC+6, until 2005; UTC+6 since).

## How it is checked

`tools/check_repo.py` reads every edition back from git on the day it took effect and compares each file, byte for
byte, with the text rebuilt from that edition, then compares the whole act word for word with the edition's HTML read
without the parser. `tools/test_repo.py` checks blame, the reader before and after known amendments, `git log
--follow`, the tags, the trailers, the authors and every command in the table above. The build is deterministic:
rebuilt from the same data, it gives the same commit hashes. See [`REPRODUCE.md`](REPRODUCE.md).

## What "author" means

The author of a commit is the law that made the change, named as the database names it (`Закон КР от 16 февраля 1996
года № 1`), at an address that cannot exist (`doc-608@cbd-minjust.invalid`, the database's document number). So `git
blame` names, for each line, the law that last wrote it. A change is credited to the edition's law when the law's text
names the article or restates the whole Constitution (`Evidence:` says which). The first texts are by the
Constitutions themselves. A change no law names (here, the database's corrections of spelling and punctuation) is by
`ЦБД ПИ Минюста КР` and labelled `Kind: unexplained`. Only the documentation commit is by Lexifina.

## What it does not show

- The 2010 Constitution and its amendments, and any law other than the Constitutions.
- Text as amended between two of the database's editions: the record has exactly the editions it publishes.
- The database's status banners and the Kyrgyz text.

This is a research aid. Only the official publications are authoritative; the database's consolidated texts, and so
this repository, are not.

## How it is built

`tools/build.py` reads the database's list of editions and each edition's text, compares consecutive editions article
by article, credits each change, and writes the commits. No AI model takes part in building or checking it. Every
step, command and decision is in [`REPRODUCE.md`](REPRODUCE.md). `corpus.json` describes the corpus for Lexifina's
global index.

## Licence

Источник: Централизованный банк данных правовой информации Министерства юстиции Кыргызской Республики,
https://cbd.minjust.gov.kg. Under the Kyrgyz law on copyright, official documents (laws, decisions and the like) are
not objects of copyright (Закон КР "Об авторском праве и смежных правах", статья 8). The database publishes no terms
of reuse, so **reuse is unclear and this repository is private**. The wording was not changed; Lexifina's own
contributions are CC0. See [`LICENSE`](LICENSE).

---

## По-русски

Конституции Кыргызской Республики в виде git-репозитория: **Конституция 5 мая 1993 года** во всех девяти редакциях
ЦБД ПИ Минюста (до замены Конституцией 2010 года) и **Конституция 5 мая 2021 года**.

- **Каждый commit — это закон**, указанный как автор: `git blame` показывает, какой закон написал каждый абзац.
- **Каждый commit датирован днем вступления закона в силу**, по словам самого закона, в полдень по Бишкеку.
- **Один файл на статью**, одна строка на абзац.
- **То, что не объясняет ни один закон, отмечено** и никакому закону не приписано.

Официальным является только текст, опубликованный в официальном издании.
