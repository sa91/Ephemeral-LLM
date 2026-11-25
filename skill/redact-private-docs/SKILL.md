---
name: redact-private-docs
description: Redact the PDFs and spreadsheets (xlsx, xlsm, xls, ods, csv, tsv) loaded in the Ephemeral LLM session and collect the redacted copies. Use when the user asks to redact their private documents, collect redacted copies, clean or end the session, or asks about its state. Never touches unredacted originals.
---

# Redact private documents (Ephemeral LLM kit)

The kit lives in `KIT_DIR`. The user loads files into a sealed, network-less container with
`./ephemeral-llm open` and uses the local model on them. Nothing is redacted until you are asked to.
Your role is the outside of that boundary.

## Redacting (the main job)

When the user asks to redact one or more PDFs or spreadsheets (`.xlsx`, `.xlsm`, `.xls`, `.ods`, `.csv`, `.tsv`), from `KIT_DIR` run it in one go with the paths they gave:

```
./ephemeral-llm redact "/path/to/a.pdf" "/path/to/b.xlsx"
```

This starts the sealed session if needed, loads the files, redacts them (about a minute and a half per page;
run it in the background for long documents) and writes the redacted copies straight into `/tmp` as
`/tmp/REDACTED_<n>_<name>.pdf` (spreadsheets: `.xlsx`, or `.csv`/`.tsv` for those; `.xlsm`, `.xls` and `.ods` come out as `.xlsx`), printing one line per file. For a spreadsheet `pages` is the number of sheets and `boxes` the number of replacements; large sheets take a minute or two per 6000 characters of new text. Folders and `.zip` files are accepted too; a zip is unpacked inside the container, never on the Mac, so do not unzip it yourself. With no paths it
redacts whatever is already loaded. When done it runs `kill` itself,
which waits until the user is no longer logged in, so the command may stay open for a while; run it in the background. The command streams the originals into the container without showing
their content; never open the originals yourself.

## Other commands you may run

- `./ephemeral-llm status` - is a session running, is the model busy, file counts
- `./ephemeral-llm out` - collect redacted copies again without queueing anything new
- `./ephemeral-llm clean [--host]` - empty the container's work area; `--host` also deletes the `/tmp/REDACTED_*` copies (pdf, xlsx, csv, tsv)
- `./ephemeral-llm kill [--outputs]` - waits until the session is idle (nobody logged in, nothing being redacted), then destroys it and writes the purge report. Never pass `--force` unless the user says so in this message. Never kill a session to make room for a test or a rebuild: if `status` shows a session, the user may be using it; defer the test until `status` says `not running`.
- `./ephemeral-llm selftest` - end-to-end check with an invented statement as PDF, xlsx and csv (needs no session running)

## What you must not do

- Do not run `open`, `chat` or `shell`. They show unredacted content and the script refuses them outside the user's own terminal. Ask the user to run them in Terminal.app (not in the Claude app's terminal panel, which you can read).
- Do not run `docker exec`, `docker cp`, `docker attach` or `docker logs` against the `ephemeral-llm` container, and do not read the user's terminal while a chat is open.
- Do not read the user's original documents, `~/PrivateRedactor/identifiers.txt`, or the `PURGE_REPORT_*.txt` files (they list where originals are stored).
- Do not read the `/tmp/REDACTED_*` files (pdf, xlsx, csv, tsv) unless the user attaches one or asks you to; they review them first (PDFs in Preview, spreadsheets in Numbers or Excel). The automatic checks only prove that identifiers that were found are gone, not that none were missed.

## Reporting

- After `redact` or `out`: repeat the per-file lines. Any `WARNING` or `FAILED` line means the user must look at that file; say so plainly. Then tell the user to review each file before sharing it: PDFs in Preview, spreadsheets in Numbers or Excel including hidden sheets. For spreadsheets also say what the copy loses: macros, images, charts, pivot tables and stored formula results (`.xls`/`.ods`: everything but the values), and that whole numbers of 7+ digits are removed unless their column header reads like an amount.
- Other files (txt, md) cannot be redacted and never leave the container.
- After `kill`: quote the `RESULT:` line. Anything other than `RESULT: PURGED` is a failure to report, not to fix silently.
- If the user says an identifier was missed, tell them to add it to `~/PrivateRedactor/identifiers.txt` themselves, then `open` the file again and ask you to redact; do not ask them to paste the identifier into the chat.
