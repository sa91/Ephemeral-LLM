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
    # page 2: the tax id beside "PAN:", the address block under the name (no label, no pattern, not in the
    # list), the mobile number and e-mail under it, two folio numbers, the two long numbers of the footer reference
    "ABCDE1234F", "12 Unit B Orchard House", "Sample Row Hilltown", "Province Province X01ab23",
    "Country - 0, Others, Country", "+41 79 555 01 23", "jonas@example.org",
    "55667788", "55667799", "7300150022", "480060913",
    # an account number after its label that the file holds in two pieces; the recipient's foreign tax number on a form
    "U76543218", "7564321876519",
    # beside cells of decimals with six places: an account id and an e-mail address
    "X9988776", "crypto.jonas@example.org",
]
MODEL_ONLY = ["Lukas Fiktiv", "Familie Testmann"]  # no pattern or list entry covers this; only the model can find it
MUST_STAY = ["US0378331005", "1,250.00", "31.12.2025", "Dividend", "INTEREST", "Statement",
             "December 1-31, 2025", "12-3456789", "Example Broker Inc",
             "Income code", "Exemption code", "Status code",
             # headings with a capitalised "Code"; the agent's tax number in the box under its label, with
             # other boxes read in between; a public form number; the institution's phone numbers in small print
             "Explanation of Codes", "Income Code", "98-7654321", "1545-0096", "800-555-0199", "+1-415-555-0100",
             # page 2: the labels of the block, the paragraph in the column beside the address, the fund lines,
             # and what is not a number in the footer reference
             "PAN:", "Mobile:", "Email:", "FOLIO NO:", "Flexi Cap Fund", "Advisor:",
             "ExampleDetailRPT_v1.2", "01-Jan-2025_31-Dec-2025",
             # page 3: the labels of the form's boxes
             "Country code", "LOB code", "Income code", "Exemption code", "Ch. 3 status code", "Ch. 4 status code",
             "Explanation of codes", "Withholding agent's name", "Primary Withholding Agent's Name"]
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


# ---------- page 2: a consolidated statement of funds ----------

ADDRESS = ["12 Unit B Orchard House", "Sample Row Hilltown", "Province Province X01ab23", "Country - 0, Others, Country"]
BLOCK = ["PAN: ABCDE1234F", "Jonas Testmann"] + ADDRESS + ["Mobile: +41 79 555 01 23", "Email: jonas@example.org"]
# a paragraph in the next column, level with the address lines: it must stay
BESIDE = ["This statement lists the", "units held in each fund", "and what was bought or", "sold during the period."]
# ISINs with a valid check digit (made up, apart from the second): letters and digits mixed, mostly digits,
# "XX" before four digits (reads like a card ending), an O beside zeros, and one the file holds in two pieces
ISINS = ["INF179K01XY4", "INE002A01018", "INF209001165", "INF1KAXX1237", "INF0000K1O01"]
SPLIT_ISIN = ("INF846K01", "EW2")
FOLIOS = ["55667788", "55667799"]
# on every page, in small print, one word up to the time: the two long numbers go, the name and the dates stay
FOOTER = "ExampleDetailRPT_v1.2_7300150022-480060913_01-Jan-2025_31-Dec-2025_-14/02/2026 9:15:20am"
FOOTER_AT, FOOTER_SIZE = (60, 828), 6


def page2():
    """[(x, y, font size, text)] of the second page"""
    items = [(60, 60, 11, "Example Registrar - Consolidated Account Statement")]
    for i, line in enumerate(BLOCK):
        items.append((60, 90 + 14 * i, 10, line))
    for i, line in enumerate(BESIDE):
        items.append((330, 90 + 14 * (2 + i), 10, line))
    y = 230
    for i, isin in enumerate(ISINS + [SPLIT_ISIN[0]]):
        title = f"B20{i}G-Sample Flexi Cap Fund {i + 1} - Direct Plan - Growth (Advisor: INA000012345/DIRECT) ISIN: {isin}"
        items += [(60, y, 8, f"FOLIO NO: {FOLIOS[i % 2]}"), (60, y + 12, 8, title),
                  (60, y + 24, 8, f"Closing Unit Balance: 81.00{i}   NAV on 31-Dec-2025: INR 12.3450")]
        y += 44
    return items


# a worksheet of dated trades under a header with the holder's name and account number: the name and the
# number go, every date, description and amount stays
TRADES_AT = 510
TRADE_COLUMNS = [(60, "Description of Currency Position"), (200, "Date Acquired"), (265, "Source"),
                 (310, "Date of Disposition"), (400, "Proceeds"), (455, "Cost"), (530, "Income or (Loss)")]
TRADES = [
    ("Forex 1200 EUR.CHF", "01/15/2025", "Trade", "01/22/2025", "1,612.45", "-412.375 EUR", "12.30"),
    ("Stock -40 XMPL", "01/15/2025", "Trade", "02/03/2025", "2,204.50", "-1,980.00", "224.50"),
    ("Forex -2300 USD.CHF", "02/11/2025", "Trade", "02/12/2025", "2,031.10", "-2,040.775 USD", "-9.675"),
    ("Stock 120 BXMP", "03/04/2025", "Trade", "03/28/2025", "960.00", "-1,015.20", "-55.20"),
    ("Forex 1200 EUR.CHF", "03/04/2025", "Trade", "03/05/2025", "1,498.00", "-412.375 EUR", "0.000"),
    ("Stock -40 XMPL", "04/01/2025", "Trade", "04/02/2025", "2,310.75", "-2,204.50", "106.25"),
    ("Forex 800 GBP.CHF", "04/01/2025", "Trade", "04/15/2025", "905.60", "-17.25 GBP", "3.001"),
    ("Stock 120 BXMP", "05/20/2025", "Trade", "06/02/2025", "1,020.00", "-960.00", "60.00"),
]
SPLIT_ACCOUNT = ("Account Number: U7654321", "8")
# quantities and prices with a small "beginning value / change" behind them: decimals are never identifiers
DECIMAL_CELLS = ["318.204517 0.000000 / 318.204517", "72.410936 2,845.119302 / -2,772.708366",
                 "$1.001200 $0.000000 / $1.001200"]


def trades():
    """[(x, y, font size, text)] of the worksheet at the foot of the second page"""
    items = [(60, TRADES_AT, 8, "Title: Jonas Testmann"), (250, TRADES_AT, 8, SPLIT_ACCOUNT[0])]
    items += [(x, TRADES_AT + 14, 8, head) for x, head in TRADE_COLUMNS]
    for i, row in enumerate(TRADES):
        items += [(x, TRADES_AT + 26 + 12 * i, 8, cell) for (x, _), cell in zip(TRADE_COLUMNS, row)]
    y = TRADES_AT + 26 + 12 * len(TRADES) + 10
    items += [(60, y, 8, "Account ID: X9988776"), (250, y, 8, "Contact crypto.jonas@example.org")]
    items += [(60 + 180 * i, y + 12, 8, cell) for i, cell in enumerate(DECIMAL_CELLS)]
    return items


# ---------- page 3: two copies of a withholding form ----------
# The agent's own name, numbers and address stand in the agent's boxes and must stay on both copies;
# what stands in the recipient's boxes goes. The labels of the boxes (the word "code" above all) stay.
AGENT = ["Example Brokers LLC", "A1B2C3.00000.LE.756", "CHE975318642", "One Example Plaza", "Greenwich CT 06830"]
FORM = [  # (line, x, label, value)
    (0, 60, "12a Withholding agent's EIN", "98-7654321"), (0, 250, "12d Withholding agent's name", AGENT[0]),
    (1, 60, "12e Withholding agent's Global Intermediary Identification Number (GIIN)", AGENT[1]),
    (1, 400, "12f Country code", "US"),
    (2, 60, "12g Foreign taxpayer identification number, if any", AGENT[2]),
    (2, 300, "12h Address (number and street)", AGENT[3]),
    (3, 60, "12i City or town, state or province, country, ZIP or foreign postal code", AGENT[4]),
    (3, 360, "14a Primary Withholding Agent's Name (if applicable)", AGENT[0]),
    (4, 60, "13a Recipient's name", "Jonas Testmann"), (4, 250, "13b Recipient's country code", "CH"),
    (4, 420, "13j LOB code", "02"),
    (5, 60, "13c Address (number and street)", "Musterweg 12"),
    (5, 250, "13i Recipient's foreign tax identification number, if any", "7564321876519"),
    (6, 60, "1 Income code", "06"), (6, 160, "4a Exemption code", "15"),
    (6, 270, "12b Ch. 3 status code", "15"), (6, 400, "12c Ch. 4 status code", "01"),
]
FORM_SMALL = "Explanation of codes: income code 06 is a dividend, status code 15 is a corporation."
FORM_COPIES = [(60, "Copy B for Recipient"), (340, "Copy C for Recipient, attach to any Federal tax return you file")]


def page3():
    """[(x, y, font size, text)] of the third page"""
    items = []
    for top, title in FORM_COPIES:
        items.append((60, top, 10, "Foreign Person's U.S. Source Income Subject to Withholding - " + title))
        for line, x, label, value in FORM:
            items += [(x, top + 22 + 30 * line, 9, label), (x, top + 34 + 30 * line, 9, value)]
        items.append((60, top + 22 + 30 * 7, 7, FORM_SMALL))
    return items


def make(path):
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in LINES:
        page.insert_text((60, y), line, fontsize=11)
        y += 20
    page.insert_text(FOOTER_AT, FOOTER, fontsize=FOOTER_SIZE)
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
    second = doc.new_page()
    for x, ty, size, line in page2() + trades():
        second.insert_text((x, ty), line, fontsize=size)
        # the rest of that ISIN, and of the account number, set a little apart as its own piece of text
        for first, rest in (SPLIT_ISIN, SPLIT_ACCOUNT):
            if line.endswith(first):
                second.insert_text((x + fitz.get_text_length(line, fontsize=size) + 2.5, ty), rest, fontsize=size)
    second.insert_text(FOOTER_AT, FOOTER, fontsize=FOOTER_SIZE)
    # a logo: a page with an image is also read by OCR, as real statements are
    logo = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 60, 30))
    logo.clear_with(170)
    second.insert_image(fitz.Rect(480, 40, 540, 70), pixmap=logo)
    third = doc.new_page()
    for x, ty, size, line in page3():
        third.insert_text((x, ty), line, fontsize=size)
    third.insert_text(FOOTER_AT, FOOTER, fontsize=FOOTER_SIZE)
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
    if SPLIT_ACCOUNT[0].split(":")[0].lower() + ": " + SPLIT_ACCOUNT[1] in blob:
        bad.append("the last piece of the account number that the file holds in two")
    lost = [s for s in MUST_STAY + BESIDE + DECIMAL_CELLS if s.lower() not in blob]
    lost += [s for s in ISINS + ["".join(SPLIT_ISIN)] if s.lower() not in squeezed]
    if text.lower().count("code") < 3 * CODE_LINES:
        lost.append('some of the "code" labels')
    if blob.count("01-jan-2025_31-dec-2025") < 2 * doc.page_count:  # in text and by_pos, on each page
        lost.append("the dates of the footer reference on one of the pages")
    # every row of the worksheet as a person reads it; the agent's details on both copies of the form;
    # every "code" of the form's labels and small print
    lost += ["trade row: " + " ".join(row) for row in TRADES if blob.count(" ".join(row).lower()) < 1]
    lost += [" ".join(head for _, head in TRADE_COLUMNS)] * (" ".join(head for _, head in TRADE_COLUMNS).lower() not in blob)
    form = " ".join(doc[2].get_text().split()).lower() if doc.page_count > 2 else ""
    planted = [value for _, _, _, value in FORM]
    lost += [f"{s} on one of the form's copies" for s in AGENT if form.count(s.lower()) < len(FORM_COPIES) * planted.count(s)]
    codes = sum(t.lower().count("code") for _, _, _, t in page3())
    if form.count("code") < codes:
        lost.append(f'{codes - form.count("code")} of the {codes} "code" on the form')
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
    print("  what is left of the invented statement: " + text[:2600])
    return 1 if bad or lost else 0


def json_meta(doc):
    return " ".join(str(v) for v in (doc.metadata or {}).values() if v)


# ---------- spreadsheets: the same invented person in an .xlsx and a .csv ----------

SHEET_MUST_GO = [
    "Jonas Testmann", "Musterweg 12", "8001 Zurich", "14.03.1987", "CH93 0076 2011 6238 5295 7",
    "jonas.testmann@example.org", "Petra Beispiel", "TESTMANN, Jonas", "J. Testmann",
    # a hyphenated account number beside its label; a whole-number customer id under its column header
    "4821-7754", "70553318",
    # the two long numbers of an underscore-joined reference
    "7300150022", "480060913",
]
SHEET_MODEL_ONLY = ["Lukas Fiktiv"]
# whole numbers under "Amount" and "Balance", decimals, transaction dates, the ISIN, labels
SHEET_MUST_STAY = ["US0378331005", "15000000", "23400000", "31000000", "1250.75", "12.4", "-300.25",
                   "31.12.2025", "30.12.2025", "29.12.2025", "28.12.2025", "Dividend", "INTEREST",
                   "Example Bank AG", "Account Number", "Customer ID", "Amount", "Booking date",
                   # the rest of the reference; ISINs with letters and digits mixed and with "XX" before four digits
                   "ExampleDetailRPT_v1.2", "01-Jan-2025_31-Dec-2025", "INF179K01XY4", "INF1KAXX1237"]
SHEET_REFERENCE = FOOTER.split("_-")[0]
CSV_HEADER = "Date;Account Number;Description;Customer ID;Amount;Price"
CSV_ROWS = [
    "31.12.2025;4821-7754;Dividend Apple Inc US0378331005;70553318;15000000;1250.75",
    "30.12.2025;4821-7754;Transfer to Petra Beispiel;70553318;23400000;-300.25",
    "29.12.2025;4821-7754;Holder Jonas Testmann, Musterweg 12, 8001 Zurich, born 14.03.1987;70553318;1200;12.40",
    "28.12.2025;4821-7754;INTEREST credit to CH93 0076 2011 6238 5295 7;70553318;900;0.50",
    f"27.12.2025;4821-7754;Purchase Sample Fund ISIN: INF1KAXX1237 ref {SHEET_REFERENCE};70553318;500;10.50",
]
CSV_MUST_GO = ["Jonas Testmann", "Musterweg 12", "8001 Zurich", "14.03.1987", "CH93 0076 2011 6238 5295 7",
               "Petra Beispiel", "4821-7754", "70553318", "7300150022", "480060913"]
CSV_MUST_STAY = [CSV_HEADER, "US0378331005", "15000000", "23400000", "1250.75", "-300.25", "12.40",
                 "31.12.2025", "28.12.2025", "Dividend", "INTEREST",
                 "INF1KAXX1237", "ExampleDetailRPT_v1.2", "01-Jan-2025_31-Dec-2025"]


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
        ["Reference", SHEET_REFERENCE],
        ["Date", "Description", "ISIN", "Customer ID", "Amount", "Price"],
        [datetime.date(2025, 12, 31), "Dividend Apple Inc", "US0378331005", 70553318, 15000000, 1250.75],
        [datetime.date(2025, 12, 30), "INTEREST credit", None, 70553318, 23400000, 12.4],
        [datetime.date(2025, 12, 29), "Transfer to Petra Beispiel", None, 70553318, 1200, -300.25],
        [datetime.date(2025, 12, 28), "Standing order Lukas Fiktiv rent", None, 70553318, 900, -900.5],
        [datetime.date(2025, 12, 27), "Purchase Sample Fund ISIN: INF1KAXX1237", "INF179K01XY4", 70553318, 500, 10.5],
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
