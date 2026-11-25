#!/usr/bin/env python3
"""Self-test helpers: make a synthetic statement with planted identifiers, and check a redacted copy.

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
]
MODEL_ONLY = ["Lukas Fiktiv", "Familie Testmann"]  # no pattern or list entry covers this; only the model can find it
MUST_STAY = ["US0378331005", "1,250.00", "31.12.2025", "Dividend", "INTEREST", "Statement",
             "December 1-31, 2025", "12-3456789", "Example Broker Inc",
             "Income code", "Exemption code", "Status code"]
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
] + ["Income code   Exemption code   Status code"] * CODE_LINES


def make(path):
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in LINES:
        page.insert_text((60, y), line, fontsize=11)
        y += 22
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


if __name__ == "__main__":
    sys.exit(make(sys.argv[2]) if sys.argv[1] == "make" else check(sys.argv[2]))
