# Ephemeral LLM - a sealed local model, with redaction on request

A local model runs inside a container that has no network, no ports and no view of the Mac's folders.
`open` puts the files you name into it so you can work on them with the model. Nothing is redacted until
you ask: `redact` (or the Claude Code skill `redact-private-docs`) produces redacted copies, and only
those come back out.

## One-time setup

```bash
colima start --cpus 8 --memory 12 --disk 40 --mount none
```

```bash
./build.sh
```

```bash
./ephemeral-llm selftest
```

Fill in `~/PrivateRedactor/identifiers.txt` (name, address, date of birth). Other name orders, initials
and date formats are derived from each entry. `redact` refuses to run while that file is empty.

`--mount none` matters: by default Colima mounts your home folder into its VM.

## Using it

Run `open` in Terminal.app, not in the Claude app's terminal panel (Claude can read that panel).

```bash
./ephemeral-llm open ~/Downloads/statements
```

```bash
./ephemeral-llm open
```

Both log you into the container: a bash prompt in `/work`. The first also loads PDFs, spreadsheets
(xlsx, xlsm, xls, ods, csv, tsv) and txt, md into `/work/docs`. Inside:

- `chat` starts the chat with the model (`/docs`, `/load 1`, `/think`, `/save`, `/exit` to return to the prompt)
- `docs` lists what is loaded
- `redact` (or `/redact` inside the chat) redacts every loaded PDF and spreadsheet not yet redacted, in the background;
  the copies stay inside until you run `./ephemeral-llm out` on the Mac
- `ollama run $MODEL`, `python` (with PyMuPDF, openpyxl) and the usual shell tools are there for anything else
- `exit` logs out and wipes the terminal

Logging out keeps the session and its files; `open` or `shell` logs you back in.

To redact in one go, with or without a session running, give the files (or ask Claude Code to):

```bash
./ephemeral-llm redact ~/Downloads/a.pdf ~/Downloads/b.xlsx
```

The redacted copies appear as `/tmp/REDACTED_<name>.pdf` (`.xlsx`, `.csv`, `.tsv` for spreadsheets), where `<name>` is the
original file name with identifiers taken out. Two files of the same name in one session give `REDACTED_<name>.pdf` and
`REDACTED_<name> (2).pdf`. A copy of the same name left in `/tmp` by an earlier session is replaced. Review each: PDFs in Preview,
spreadsheets in Numbers or Excel, hidden sheets included. When you are finished with the model:

```bash
./ephemeral-llm kill
```

| Command | What it does |
|---|---|
| `open [file or folder] ...` | starts the sealed session if needed, streams the files into container RAM, logs you into the container. Redacts nothing. Your terminal only. |
| `redact [file or folder] ...` | one go: starts the session if needed, loads the given PDFs and spreadsheets, redacts every loaded one not yet redacted, and writes the copies into `/tmp` as `REDACTED_*` (pdf, xlsx, csv, tsv). A `.zip` is unpacked inside the container, in RAM, and every PDF and spreadsheet in it is redacted; password-protected zips and zips inside zips are refused. With no paths, redacts what is already loaded. When done it runs `kill`, which waits until nobody is logged in. |
| `out` | collects redacted copies again without queueing anything |
| `clean [--host]` | empties the container work area; `--host` also deletes the `/tmp/REDACTED_*` copies (pdf, xlsx, csv, tsv) |
| `kill [--force] [--outputs]` | waits until the session is idle (nothing being redacted, nobody logged in or chatting), collects any redacted copies still inside, then removes the container and writes `~/PrivateRedactor/evidence/PURGE_REPORT_<time>.txt`. `--force` ends it at once; `--outputs` also deletes the `/tmp/REDACTED_*` copies. |
| `shell` | log back into the running session without loading anything. Your terminal only. |
| `chat` | go straight into the chat from the Mac. Your terminal only. |
| `status` | running, network mode, model busy/idle, file counts |
| `selftest` | full run on an invented statement (a PDF of 3 pages, an xlsx with a hidden sheet, a csv loaded twice) in its own container: load, redact, out, clean, kill, purge report. `open` is refused while it runs. |

## Reading the redaction summary

- `ok` - nothing found again in the output, by text search or by OCR of the rendered pages.
- `WARNING ... CHECK` - a scan, a page where the model failed, OCR still reads something identifier-like, or a workbook had images, charts or pivot tables (they are left out of the copy). Look at that file.
- `LEAK` - identifier text the kit itself found was still in the saved file. The copy is handed out anyway so it can be
  reviewed and the rule fixed, but it must not be shared: fix the rule and redact the file again.
- `FAILED` - the file could not be opened (password-protected, damaged); nothing was produced.

What the PDF rules add to the patterns, your list and the model:

- An address printed as a block is removed by where it stands: the lines between the holder's name (or a `PAN:` / `Name:`
  line) and a `Mobile:` / `Phone:` / `Email:` line under it, in the same left-aligned column. Lines of the form `Label: value`
  in between stay, and so does text in a column beside the block.
- In an underscore-joined reference such as `Report_v1.2_7300150022-480060913_01-Jan-2025`, the numbers of 7 or more digits
  are removed on every page; the report name and the dates stay.
- An ISIN with a valid check digit is always kept, also where OCR misreads it on a page that has images.
- On a form, what stands in the boxes of the withholding agent, payer or employer (name, GIIN, tax numbers, address) is kept on
  every copy; what stands in the recipient's boxes is removed. A numbered box such as `12h Address` belongs to whoever owns
  another box of that number (`12a Withholding agent's EIN`).
- In a table of dated trades the model alone cannot remove anything but a person's name: dates, descriptions, quantities,
  tickers and amounts stay unless a pattern or your list matches them. Decimal numbers are never taken apart.
- An account number after its label that the file holds in two pieces (`U1234567` and `8`) is removed whole.

`ok` means everything that was *found* is gone. It cannot mean nothing was *missed*. Your review in Preview is the
last check; add misses to `identifiers.txt`, `open` the file again and redact again.

## Spreadsheets

`.xlsx`, `.xlsm`, `.xls`, `.ods`, `.csv` and `.tsv` are redacted cell by cell; in `pages=` the summary shows the number of sheets
and in `boxes=` the number of replacements. A removed value becomes `[REDACTED]`, the rest of the cell stays.

- Text cells: the patterns, your list and the model, as for PDFs. A label reaches a number in the next cell of the row or under
  it in the column ("Account Number" beside or above the value), and a name split over two columns is found.
- Whole numbers with 7 or more digits are removed, unless the column label above them reads like money or a quantity (amount,
  balance, value, total, price, qty, quantity, shares, betrag, saldo, kurs, wert, usd, chf, eur, gbp). Decimals are never touched.
  A large whole-number amount under a header that is not in that list is removed; an account number under a header that is in it stays.
- Date cells are removed only if they are a date from your list or stand beside or under a birth-date label; transaction dates stay.
- Sheet names, comments, link targets, headers and footers, defined names and input rules are redacted or removed; document
  properties and comment authors are cleared. Hidden sheets, rows and columns are treated like visible ones.
- What the copy loses: `.xlsx`/`.xlsm` keep formatting and formulas, but not macros, images, charts, text boxes, pivot tables, links to
  other workbooks, or the last calculated result of a formula (open the copy in Excel or Numbers to recalculate; a formula that used a
  removed value or a renamed sheet shows an error). `.xlsm` comes out as `.xlsx`. `.xls` and `.ods` come out as a plain `.xlsx` with
  values only. `.csv`/`.tsv` keep their delimiter and encoding.
- The model reads each different cell value once, in parts of about 6000 characters, and at most 40 parts per file
  (`SHEET_MODEL_CALLS`); a larger sheet gets `CHECK` and the rest is covered by the patterns and your list only. Expect a minute or two per part.
- Password-protected workbooks cannot be opened and are reported as `FAILED`.

## The model

`config.sh` sets `MODEL` (default `qwen3.5:9b-q4_K_M`, 6.6 GB). It is the largest current Qwen that fits a
16 GB Mac inside the VM. Docker on a Mac has no GPU access, so it runs on CPU: expect a few words per second.
A larger model does not fit; a smaller one (`MODEL=qwen3.5:4b-q4_K_M ./build.sh`) is about twice as fast.
Close heavy apps during a session: the VM may use up to 12 of the Mac's 16 GB.

## GPU variant (optional, about twice as fast)

`./ephemeral-llm-gpu` is the same sealed session in a second Colima VM of type krunkit, which passes the
Mac's GPU into the container as one device. Measured on an M1 Pro: 59-60 s for the self-test set against
90-151 s on the CPU kit. Only one of the two VMs fits in 16 GB, so you switch between them:

```bash
./ephemeral-llm-gpu vm-start
```

```bash
./ephemeral-llm-gpu build
```

```bash
./ephemeral-llm-gpu open ~/Downloads/statements
```

```bash
./ephemeral-llm-gpu vm-stop
```

`vm-start` stops the CPU VM (refused while a session is running) and starts the GPU one; `vm-stop` does the
reverse. `build` is needed once and takes about 21 GB inside the VM while it runs; a krunkit VM keeps Docker's
data on its root disk, so `vm-start` sizes that at 40 GB (`GPU_VM_ROOT_DISK`). Every other command is the same as `./ephemeral-llm`, including `redact`,
`kill` and `selftest`. At start it prints the device the model landed on, for example
`model device: Vulkan0: Virtio-GPU Venus (Apple M1 Pro)`.

Differences from the CPU kit: the model runs on llama.cpp's Vulkan server from the RamaLama image instead of
Ollama (so `ollama run` is not available inside), the container has exactly one device (`/dev/dri`), which the
seal check counts, and the GPU path into the VM is newer and less tested than a CPU-only container.

## What is and is not guaranteed

- Enforced by Docker and checked on every start: `--network none`, no mounts, no ports, read-only root, no
  capabilities, non-root user, swap off for the container, `/work` in RAM only.
- Not enforceable by this kit: anything running as your macOS user (including Claude Code) can talk to Docker and
  could `docker exec` into a running session. The script refuses `open`/`chat`/`shell` from Claude Code, the skill
  forbids the rest, and `.claude/settings.json` denies those commands. A long-lived session widens this window:
  `kill` when you are done with the files.
- Loaded files, the chat and saved notes stay in container RAM until `clean` or `kill`.
- Only PDFs and spreadsheets can be redacted. Other loaded files (txt, md) never leave the container.

## Files

`config.sh` settings · `build.sh` image build, pins the base image digest in `container/base.lock` ·
`ephemeral-llm` host CLI · `verify_purge.sh` purge checks · `container/` Dockerfile, entrypoint, `redact.py`,
`chat.py`, `selftest.py` · `identifiers.example.txt` template · `skill/redact-private-docs/` Claude Code skill.
