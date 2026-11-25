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

Both log you into the container: a bash prompt in `/work`. The first also loads PDFs (and txt, md, csv)
into `/work/docs`. Inside:

- `chat` starts the chat with the model (`/docs`, `/load 1`, `/think`, `/save`, `/exit` to return to the prompt)
- `docs` lists what is loaded
- `redact` (or `/redact` inside the chat) redacts every loaded PDF not yet redacted, in the background;
  the copies stay inside until you run `./ephemeral-llm out` on the Mac
- `ollama run $MODEL`, `python` (with PyMuPDF) and the usual shell tools are there for anything else
- `exit` logs out and wipes the terminal

Logging out keeps the session and its files; `open` or `shell` logs you back in.

To redact in one go, with or without a session running, give the files (or ask Claude Code to):

```bash
./ephemeral-llm redact ~/Downloads/a.pdf ~/Downloads/b.pdf
```

The redacted copies appear as `/tmp/REDACTED_<n>_<name>.pdf`. Review each in Preview. When you are finished with the model:

```bash
./ephemeral-llm kill
```

| Command | What it does |
|---|---|
| `open [file or folder] ...` | starts the sealed session if needed, streams the files into container RAM, logs you into the container. Redacts nothing. Your terminal only. |
| `redact [pdf or folder] ...` | one go: starts the session if needed, loads the given PDFs, redacts every loaded PDF not yet redacted, and writes the copies into `/tmp` as `REDACTED_*.pdf`. A `.zip` is unpacked inside the container, in RAM, and every PDF in it is redacted; password-protected zips and zips inside zips are refused. With no paths, redacts what is already loaded. When done it runs `kill`, which waits until nobody is logged in. |
| `out` | collects redacted copies again without queueing anything |
| `clean [--host]` | empties the container work area; `--host` also deletes `/tmp/REDACTED_*.pdf` |
| `kill [--force] [--outputs]` | waits until the session is idle (nothing being redacted, nobody logged in or chatting), collects any redacted copies still inside, then removes the container and writes `~/PrivateRedactor/evidence/PURGE_REPORT_<time>.txt`. `--force` ends it at once; `--outputs` also deletes `/tmp/REDACTED_*.pdf`. |
| `shell` | log back into the running session without loading anything. Your terminal only. |
| `chat` | go straight into the chat from the Mac. Your terminal only. |
| `status` | running, network mode, model busy/idle, file counts |
| `selftest` | full run on an invented statement in its own container: load, redact, out, clean, kill, purge report. `open` is refused while it runs. |

## Reading the redaction summary

- `ok` - nothing found again in the output, by text search or by OCR of the rendered pages.
- `WARNING ... CHECK` - a scan, a page where the model failed, or OCR still reads something identifier-like. Look at that file.
- `FAILED` - identifier text was still in the saved file. The output was withheld and never left the container.

`ok` means everything that was *found* is gone. It cannot mean nothing was *missed*. Your review in Preview is the
last check; add misses to `identifiers.txt`, `open` the file again and redact again.

## The model

`config.sh` sets `MODEL` (default `qwen3.5:9b-q4_K_M`, 6.6 GB). It is the largest current Qwen that fits a
16 GB Mac inside the VM. Docker on a Mac has no GPU access, so it runs on CPU: expect a few words per second.
A larger model does not fit; a smaller one (`MODEL=qwen3.5:4b-q4_K_M ./build.sh`) is about twice as fast.
Close heavy apps during a session: the VM may use up to 12 of the Mac's 16 GB.

## What is and is not guaranteed

- Enforced by Docker and checked on every start: `--network none`, no mounts, no ports, read-only root, no
  capabilities, non-root user, swap off for the container, `/work` in RAM only.
- Not enforceable by this kit: anything running as your macOS user (including Claude Code) can talk to Docker and
  could `docker exec` into a running session. The script refuses `open`/`chat`/`shell` from Claude Code, the skill
  forbids the rest, and `.claude/settings.json` denies those commands. A long-lived session widens this window:
  `kill` when you are done with the files.
- Loaded files, the chat and saved notes stay in container RAM until `clean` or `kill`.
- Only PDFs can be redacted. Other loaded files never leave the container.

## Files

`config.sh` settings · `build.sh` image build, pins the base image digest in `container/base.lock` ·
`ephemeral-llm` host CLI · `verify_purge.sh` purge checks · `container/` Dockerfile, entrypoint, `redact.py`,
`chat.py`, `selftest.py` · `identifiers.example.txt` template · `skill/redact-private-docs/` Claude Code skill.
