#!/usr/bin/env python3
"""Self-test helpers: make a synthetic statement (PDF, xlsx, csv) with planted identifiers, and check a redacted copy.

All data here is invented; none of it is the user's.
"""
import sys

import fitz

MUST_GO = [
    "Jonas Testmann", "Musterweg 12", "8001 Zurich", "14.03.1987",
    "CH93 0076 2011 6238 5295 7", "UBSWCHZH80A", "40-12-34", "12345678",
    "jonas.testmann@example.org", "+41 44 555 01 23", "9912", "AB12CD34EF",
    "Petra Beispiel", "912-70-1234", "1 4 0 3 1 9 8 7",
    # forms the identifiers list does not spell out: derived from "Jonas Testmann" and "14.03.1987"
    "TESTMANN, Jonas", "1987-03-14", "March 14, 1987", "J. Testmann",
    # account number in two groups under its label; a form id printed one digit per box
    "4821-7754", "7305518264",
    # the recipient's tax number in a form box, under its label
    "45-6789012",
]
MODEL_ONLY = ["Lukas Fiktiv", "Familie Testmann"]  # no pattern or list entry covers this; only the model can find it
MUST_STAY = ["US0378331005", "1,250.00", "31.12.2025", "Dividend", "INTEREST", "Statement",
             "December 1-31, 2025", "12-3456789", "Example Broker Inc",
             "Income code", "Exemption code", "Status code",
             # headings with a capitalised "Code"; the agent's tax number in the box under its label, with
             # other boxes read in between; a public form number; the institution's phone numbers in small print
             "Explanation of Codes", "Income Code", "98-7654321", "1545-0096", "800-555-0199", "+1-415-555-0100"]
CODE_LINES = 4  # label lines with the word "code" three times each: none of them may be lost
BOXED_STAY = "40219"  # a short boxed value that is not an identifier

LINES = [
    "Example Bank AG - Account Statement",
    "Holder: Jonas Testmann, Musterweg 12, 8001 Zurich",
    "Date of birth: 14.03.1987   Customer ID: AB12CD34EF",
    "IBAN: CH93 0076 2011 6238 5295 7   BIC: UBSWCHZH80A",
    "Sort code: 40-12-34   Account number: 12345678",
    "Contact: jonas.testmann@example.org  +41 44 555 01 23",
    "Card ending 9912   US TIN: 912-70-1234",
    "Recipient: TESTMANN, Jonas  born 1987-03-14 (March 14, 1987)  signed J. Testmann",
    "Household: Familie Testmann",
    "Account Number   Statement Period",
    "4821-7754   December 1-31, 2025",
    "",
    "31.12.2025  Dividend  Apple Inc  ISIN US0378331005      1,250.00 USD",
    "30.12.2025  INTEREST  credit                                12.40 USD",
    "29.12.2025  Transfer to Petra Beispiel                     -300.00 USD",
    "28.12.2025  Standing order Lukas Fiktiv rent              -900.00 USD",
    "",
    "Withholding agent's name Example Broker Inc   Withholding agent's EIN 12-3456789",
    "Explanation of Codes",
    "Income Code 06   OMB No. 1545-0096",
    "12a Withholding agent's EIN   12b Ch. 3 status code   12c Ch. 4 status code",
    "98-7654321   15   01",
    "8 Recipient's U.S. TIN   9a Ch. 3 status code   9b Ch. 4 status code",
    "45-6789012   16   02",
] + ["Income code   Exemption code   Status code"] * CODE_LINES + [
    "Questions about this statement? Please call us at 800-555-0199 or +1-415-555-0100.",
    "Example Broker Inc is not a tax adviser and does not give tax or legal advice to clients.",
]


def make(path):
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in LINES:
        page.insert_text((60, y), line, fontsize=11)
        y += 20
    # boxed digits, as on tax forms: every digit is its own piece of text, and the file
    # does not hold them in reading order, so only their position on the page gives the number
    for row, (digits, order) in enumerate((("14031987", (3, 0, 6, 1, 7, 4, 2, 5)),
                                           ("7305518264", (4, 9, 0, 7, 2, 5, 1, 8, 3, 6)),
                                           (BOXED_STAY, (2, 0, 4, 1, 3)))):
        for i in order:
            page.insert_text((60 + i * 22, y + 20), digits[i], fontsize=11)
        y += 22
    # a form field and metadata, which a viewer shows or hides differently
    w = fitz.Widget()
    w.field_name, w.field_type = "recipient", fitz.PDF_WIDGET_TYPE_TEXT
    w.rect, w.field_value = fitz.Rect(60, y + 40, 320, y + 60), "Jonas Testmann"
    page.add_widget(w)
    doc.set_metadata({"author": "Jonas Testmann", "title": "Statement 12345678"})
    doc.save(path)


def check(path):
    doc = fitz.open(path)
    text = " ".join(" ".join(p.get_text().split()) for p in doc)
    # the same words by position (top to bottom, left to right), as a person reads boxed digits
    by_pos = " ".join(w[4] for p in doc for w in sorted(p.get_text("words"), key=lambda w: (round(w[3]), w[0])))
    fields = " ".join(str(w.field_value) for p in doc for w in p.widgets())
    blob = (text + " " + by_pos + " " + fields + " " + json_meta(doc)).lower()
    squeezed = blob.replace(" ", "")
    bad = [s for s in MUST_GO if s.lower() in blob or s.lower().replace(" ", "") in squeezed]
    lost = [s for s in MUST_STAY if s.lower() not in blob]
    if text.lower().count("code") < 3 * CODE_LINES:
        lost.append('some of the "code" labels')
    if BOXED_STAY not in squeezed:
        lost.append("short boxed value")
    print(f"planted identifiers still present: {len(bad)}; kept-on-purpose values lost: {len(lost)}")
    for s in bad:
        print(f"  STILL PRESENT: {s}")
    for s in lost:
        print(f"  LOST: {s}")
    missed = [s for s in MODEL_ONLY if s.lower() in blob]
    print(f"  model layer: found {len(MODEL_ONLY) - len(missed)} of {len(MODEL_ONLY)} names that only the model could find"
          + ("" if not missed else "  <- MISSED; this is why your own review is required"))
    print("  what is left of the invented statement: " + text[:900])
    return 1 if bad or lost else 0


def json_meta(doc):
    return " ".join(str(v) for v in (doc.metadata or {}).values() if v)


# ---------- spreadsheets: the same invented person in an .xlsx and a .csv ----------

SHEET_MUST_GO = [
    "Jonas Testmann", "Musterweg 12", "8001 Zurich", "14.03.1987", "CH93 0076 2011 6238 5295 7",
    "jonas.testmann@example.org", "Petra Beispiel", "TESTMANN, Jonas", "J. Testmann",
    # a hyphenated account number beside its label; a whole-number customer id under its column header
    "4821-7754", "70553318",
]
SHEET_MODEL_ONLY = ["Lukas Fiktiv"]
# whole numbers under "Amount" and "Balance", decimals, transaction dates, the ISIN, labels
SHEET_MUST_STAY = ["US0378331005", "15000000", "23400000", "31000000", "1250.75", "12.4", "-300.25",
                   "31.12.2025", "30.12.2025", "29.12.2025", "28.12.2025", "Dividend", "INTEREST",
                   "Example Bank AG", "Account Number", "Customer ID", "Amount", "Booking date"]
CSV_HEADER = "Date;Account Number;Description;Customer ID;Amount;Price"
CSV_ROWS = [
    "31.12.2025;4821-7754;Dividend Apple Inc US0378331005;70553318;15000000;1250.75",
    "30.12.2025;4821-7754;Transfer to Petra Beispiel;70553318;23400000;-300.25",
    "29.12.2025;4821-7754;Holder Jonas Testmann, Musterweg 12, 8001 Zurich, born 14.03.1987;70553318;1200;12.40",
    "28.12.2025;4821-7754;INTEREST credit to CH93 0076 2011 6238 5295 7;70553318;900;0.50",
]
CSV_MUST_GO = ["Jonas Testmann", "Musterweg 12", "8001 Zurich", "14.03.1987", "CH93 0076 2011 6238 5295 7",
               "Petra Beispiel", "4821-7754", "70553318"]
CSV_MUST_STAY = [CSV_HEADER, "US0378331005", "15000000", "23400000", "1250.75", "-300.25", "12.40",
                 "31.12.2025", "28.12.2025", "Dividend", "INTEREST"]


def make_xlsx(path):
    import datetime
    import openpyxl
    from openpyxl.comments import Comment
    from openpyxl.workbook.defined_name import DefinedName
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Statement"
    birth = datetime.date(1987, 3, 14)
    rows = [
        ["Example Bank AG - Account Statement"],
        ["Holder", "Jonas Testmann"],
        ["Address", "Musterweg 12, 8001 Zurich"],
        ["IBAN", "CH93 0076 2011 6238 5295 7"],
        ["Account Number", "4821-7754"],
        ["Date of birth", birth],  # a real date cell, as are the transaction dates
        ["Contact", "jonas.testmann@example.org"],
        [],
        ["Date", "Description", "ISIN", "Customer ID", "Amount", "Price"],
        [datetime.date(2025, 12, 31), "Dividend Apple Inc", "US0378331005", 70553318, 15000000, 1250.75],
        [datetime.date(2025, 12, 30), "INTEREST credit", None, 70553318, 23400000, 12.4],
        [datetime.date(2025, 12, 29), "Transfer to Petra Beispiel", None, 70553318, 1200, -300.25],
        [datetime.date(2025, 12, 28), "Standing order Lukas Fiktiv rent", None, 70553318, 900, -900.5],
    ]
    for row in rows:
        ws.append(row)
    # places a reviewer does not see at a glance: a comment, a link, the footer, a name, the properties
    ws["B2"].comment = Comment("Checked with Jonas Testmann", "Jonas Testmann")
    ws["B7"].hyperlink = "mailto:jonas.testmann@example.org"
    ws.oddFooter.center.text = "Jonas Testmann"
    wb.defined_names["Owner"] = DefinedName("Owner", attr_text='"Jonas Testmann"')
    wb.properties.creator = wb.properties.lastModifiedBy = "Jonas Testmann"
    wb.properties.title = "Statement 70553318 Jonas Testmann"
    hidden = wb.create_sheet("Jonas Testmann")
    hidden.sheet_state = "hidden"
    for row in (["Recipient: TESTMANN, Jonas"],
                ["Birth date", "Booking date", "Customer ID", "Balance"],
                [birth, datetime.date(2025, 12, 31), 70553318, 31000000],
                ["signed J. Testmann"]):
        hidden.append(row)
    wb.save(path)


def make_csv(path):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join([CSV_HEADER] + CSV_ROWS) + "\n")


def xlsx_text(path):
    """(cell values, everything else): every string a reader of the file could get at."""
    import datetime
    import html
    import zipfile
    import openpyxl
    wb = openpyxl.load_workbook(path)
    cells, rest = [], []
    for ws in wb.worksheets:
        rest.append(ws.title)
        rest += [part.text or "" for hf in (ws.oddHeader, ws.oddFooter, ws.evenHeader, ws.evenFooter)
                 for part in (hf.left, hf.center, hf.right)]
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if isinstance(v, datetime.date):
                    v = f"{v.day:02}.{v.month:02}.{v.year}"
                if v is not None:
                    cells.append(str(v))
                if c.comment:
                    rest += [c.comment.text or "", c.comment.author or ""]
                if c.hyperlink:
                    rest.append(str(c.hyperlink.target))
    rest += [str(v) for v in vars(wb.properties).values() if isinstance(v, str)]
    with zipfile.ZipFile(path) as zf:  # and the file as it is stored
        rest += [html.unescape(zf.read(n).decode("utf-8", "replace")) for n in zf.namelist()]
    state = [ws.sheet_state for ws in wb.worksheets]
    return cells, rest, state


def check_sheet(path):
    kind = path.rsplit(".", 1)[-1].lower()
    lost = []
    if kind == "csv":
        text = open(path, encoding="utf-8").read()
        kept, blob = text, text.lower()
        must_go, must_stay, model_only = CSV_MUST_GO, CSV_MUST_STAY, []
        if len(text.splitlines()) != 1 + len(CSV_ROWS):
            lost.append("a row of the table")
    else:
        cells, rest, state = xlsx_text(path)
        kept, blob = " | ".join(cells), " ".join(cells + rest).lower()
        must_go, must_stay, model_only = SHEET_MUST_GO, SHEET_MUST_STAY, SHEET_MODEL_ONLY
        if state != ["visible", "hidden"]:
            lost.append("the hidden sheet, or its hidden state")
    squeezed = blob.replace(" ", "")
    bad = [s for s in must_go if s.lower() in blob or s.lower().replace(" ", "") in squeezed]
    lost += [s for s in must_stay if s.lower() not in kept.lower()]
    print(f"{kind}: planted identifiers still present: {len(bad)}; kept-on-purpose values lost: {len(lost)}")
    for s in bad:
        print(f"  STILL PRESENT: {s}")
    for s in lost:
        print(f"  LOST: {s}")
    missed = [s for s in model_only if s.lower() in blob]
    if model_only:
        print(f"  model layer: found {len(model_only) - len(missed)} of {len(model_only)} names that only the model could find"
              + ("" if not missed else "  <- MISSED; this is why your own review is required"))
    print(f"  what is left of the invented {kind}: " + " ".join(kept.split())[:700])
    return 1 if bad or lost else 0


if __name__ == "__main__":
    import os
    if not os.path.exists(sys.argv[2]) and sys.argv[1] == "check":
        print("no redacted copy to check (withheld, or not produced)")
        sys.exit(1)
    ext = sys.argv[2].rsplit(".", 1)[-1].lower()
    if sys.argv[1] == "make":
        sys.exit({"pdf": make, "xlsx": make_xlsx, "csv": make_csv}[ext](sys.argv[2]))
    sys.exit(check(sys.argv[2]) if ext == "pdf" else check_sheet(sys.argv[2]))
