---
name: redacted-task
description: Work on a redacted file from the Ephemeral LLM kit - review how well it was redacted, do the task the user asked for on it, then plan redaction improvements, get approval and launch a background agent to make them. Use when the user attaches or names a REDACTED_*.pdf, REDACTED_*.xlsx, REDACTED_*.csv or REDACTED_*.tsv (or any file redacted by the kit) together with a task or question, or invokes /redacted-task.
---

# Redacted-file task (Ephemeral LLM kit)

The kit lives in `KIT_DIR`. The user redacts documents in a sealed local container and hands the redacted
copies to you. Every time, do these four things in this order. The task can be anything about the file:
extract figures, fill a table, compute, summarise, compare, answer a question.

Arguments: the redacted file(s) and the task, in any order. If no file is named, use the files attached to
the message; if none, ask which `/tmp/REDACTED_*` file (pdf, xlsx, csv, tsv) is meant. Read only the files the user points to.
The copies are named `REDACTED_<name>.<ext>` with no running number; a second file of the same name in one
session is `REDACTED_<name> (2).<ext>`.

## 1. Review the redaction

If the kit reported a file as `LEAK`, start with that file: the kit itself still found identifier text in it. Say where, by kind and place, and put its fix first in step 3.

Read every page of each file (PDFs over 10 pages: in page ranges). For a spreadsheet read every sheet, hidden ones too, and also
comments, sheet names and document properties; removed values show as `[REDACTED]`. Look for:

- **Misses** - anything that identifies a private person or their accounts and is still readable: names,
  addresses, dates of birth, account/customer/tax/reference numbers, email, phone, values printed one
  character per box, text inside images, barcodes with readable text, the file name itself.
- **Over-redaction** - things removed that are not personal and are useful: amounts, dates, ISINs, security
  names, the institution's own name/tax number/address, ordinary words or labels; in a spreadsheet also whole-number
  amounts or quantities removed because their column header does not read like an amount.
- **Inconsistency** - the same field removed on one page or copy and visible on another.

Describe each finding by kind and place ("an account number in the header of page 1"), never by repeating
the value. Do not copy a missed identifier into your reply, into files, into memory, or into an agent brief.

## 2. Do the task

Then answer what was asked, using only what is in the files.

- Tie every figure to its file and page. Say which figures are printed and which you derived, and how.
- If redaction removed something the task needs, say so instead of guessing.
- Check the document is what its name says (year, account, form type) and flag a mismatch.
- For tax or legal rules: look them up from official sources rather than memory, mark what you could not
  verify, say you are not a tax professional, and name who decides (for Swiss tax: a Treuhänder or the
  cantonal tax office).
- Do arithmetic explicitly; show the sum when it is not a single printed number.

## 3. Plan improvements and get approval

If step 1 found nothing, say "redaction: no issues found" and stop here.

Otherwise list the proposed fixes, misses first, each as one line: what kind of thing, where the rule would
go (a fixed pattern, the model prompt, the candidate filter, the box/position matching, or for spreadsheets the
cell, row and column-header rules), and the invented
test case that would prove it. Then ask for approval and wait. Do not edit the kit or start an agent before
the user approves. They may approve all, some, or none.

## 4. Launch a background agent for the approved fixes

Start one background agent (Agent tool, general-purpose). Its brief must contain:

- Scope: work only in `KIT_DIR`; read `README.md`, `container/redact.py`, `container/selftest.py` and
  `cmd_selftest` in `ephemeral-llm` first.
- The approved fixes, described by kind with **invented** example values only.
- Hard rules: never read `~/PrivateRedactor`, the user's originals, or any `REDACTED_*` file; never run
  `docker exec/cp/logs/attach`, `./ephemeral-llm open|chat|shell|kill|clean`; no commits.
- Each fix gets a planted case in `container/selftest.py` (`MUST_GO` / `MUST_STAY` for the PDF, `SHEET_MUST_GO` / `SHEET_MUST_STAY`
  and `CSV_MUST_GO` / `CSV_MUST_STAY` for spreadsheets).
- Testing: `./build.sh`, then `./ephemeral-llm selftest` and `./ephemeral-llm selftest --no-list`
  (10-minute timeouts). If the self-test reports that a session exists, the user is using the model: never kill
  it. Wait and retry `./ephemeral-llm status` every few minutes for up to 30 minutes; test once it says
  `not running`, otherwise report the change as built but untested.
- Done means both self-tests print `SELFTEST PASSED` with 0 planted identifiers left and 0 kept values
  lost, for the PDF, the xlsx and the csv. Report what changed per fix, the final test lines, anything unverified, and new false-positive risks.

Tell the user the agent is running, that the self-test cannot run while they have a session open, and that
files already in `/tmp` keep the old redaction until they are redacted again.

When the agent reports back, check its claims before repeating them: run `./ephemeral-llm selftest` yourself
only if `status` says `not running` (never kill the user's session for this; defer until it is gone), and read the diff of `container/redact.py` for anything that weakens an existing
check. Then tell the user what is fixed, what is not, and that they should redact the file again.

## Things that stay off limits to you

- `./ephemeral-llm open`, `chat`, `shell`, and `docker exec/cp/attach/logs` on the container.
- `~/PrivateRedactor/identifiers.txt`, the purge reports, and the user's original documents.
- Other `/tmp/REDACTED_*` files the user did not point you to.
