"""Build data/processed/contracts.csv from the CUAD full contract texts.

Source: CUAD v1 (https://zenodo.org/records/4595826), folder full_contract_txt.
Each .txt file is one contract.

The title and the preamble (parties, date, recitals) are removed, because the
title names the contract type (for example DISTRIBUTOR AGREEMENT) and would
let a model recognise contracts without reading their content.

Run from the repo root:  python src/clean_cuad.py
"""
import glob
import os
import random
import re
from collections import Counter
import pandas as pd

# ====== Settings ======
RAW_DIR = r"E:\CUAD\CUAD_v1\CUAD_v1\full_contract_txt"  # change to your local path
OUT_PATH = "data/processed/contracts.csv"
EXTRA_PATH = "data/extra/cuad_files.csv"   # file names, for traceability only
MIN_WORDS, MAX_WORDS = 10, 250
RANDOMIZE_LENGTH = True    # cut each contract at a random length to avoid a length shortcut
MIN_TRUNC = 50
SEARCH_WORDS = 600         # look for the end of the preamble inside the first N words
PREAMBLE_SKIP = 80         # fallback: skip this many words when no marker is found
SEED = 42
# ======================

LEAD_NUMBERS = re.compile(r"^\s*(?:\d+(?:\.\d+)*\.?\s+){2,}")       # table-of-contents numbers
LEAD_SINGLE = re.compile(r"^\s*\d{1,2}\s+(?=[A-Za-z])")             # lone page number
LEAD_EXHIBIT = re.compile(r"(?i)^\s*exhibits?\s+\S+\s*=?\s*")       # Exhibit A / 10.1 / (k)(1)
CONF_FLAG = re.compile(
    r"(?i)redacted|confidential treatment|confidentiality request|"
    r"(?:has|have) been omitted|omits the information|\{\*+\}|c\.f\.r\."
)
AGREE_AS_FOLLOWS = re.compile(r"(?i)\bagree[sd]?\s+(?:as\s+follows|to\s+the\s+following)\s*[:.;,]?")
NOW_THEREFORE = re.compile(r"(?i)\bnow,?\s+therefore\b")
# EDGAR page footer, for example: "Source: NEUROBO PHARMACEUTICALS, INC., S-4, 9/3/2019"
SOURCE_FOOTER = re.compile(
    r"(?:\b\d{1,3}\s+)?Source:\s+.{3,150}?,\s*[^,]{2,25},\s*\d{1,2}/\d{1,2}/\d{2,4}"
)
# Leading enumeration of the first clause: "1.", "2.1", "A.", "(a)"
LEADING_ENUM = re.compile(r"^\s*(?:(?:\d+(?:\.\d+)*\.?|[A-Za-z]\.|\([A-Za-z0-9]{1,3}\))\s+)+")

def clean_text(t):
    t = re.sub(r"\[[\s*]+\]", " ", t)                                  # [* * *] marks
    t = re.sub(r"(?im)^\s*page\s+\d+(\s+of\s+\d+)?\s*$", " ", t)       # page numbers on their own line
    t = re.sub(r"[_=\-]{4,}", " ", t)                                  # separator lines
    t = re.sub(r"(?i)\(\s*execution\s+(?:version|copy)[^)]*\)", " ", t)
    t = re.sub(r"(?i)\bexecution\s+(?:version|copy)\b", " ", t)
    t = re.sub(r"\bX{4,}\b", " ", t)                                   # XXXX redaction (same as CFPB)
    # SEC confidentiality headers: remove the sentence, keep the contract
    t = re.sub(r"(?i)information\s+in\s+this\s+exhibit[^.]*\.", " ", t)
    t = re.sub(r"(?i)certain\s+(?:identified\s+)?information[^.]*?(?:omitted|redacted)[^.]*\.", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = SOURCE_FOOTER.sub(" ", t)                                      # EDGAR page footers
    t = re.sub(r"\s+", " ", t).strip()
    for _ in range(4):                                                 # leading numbers / exhibit marks
        t = LEAD_NUMBERS.sub("", t)
        t = LEAD_SINGLE.sub("", t)
        t = LEAD_EXHIBIT.sub("", t)
    return t.strip()


def cut_preamble(text):
    """Remove the title and preamble. Returns (body, method)."""
    words = text.split()
    limit = len(" ".join(words[:SEARCH_WORDS]))   # text is already single-spaced

    m = AGREE_AS_FOLLOWS.search(text, 0, limit)
    if m:
        body = text[m.end():].lstrip(" :;.,-")
        if len(body.split()) >= MIN_TRUNC:
            return body, "agree-as-follows"

    m = NOW_THEREFORE.search(text, 0, limit)
    if m:
        tail = text[m.end():m.end() + 500]
        end = re.search(r"[:;.]", tail)
        if end:
            body = text[m.end() + end.end():].lstrip(" :;.,-")
            if len(body.split()) >= MIN_TRUNC:
                return body, "now-therefore"

    if len(words) > PREAMBLE_SKIP + MIN_TRUNC:
        return " ".join(words[PREAMBLE_SKIP:]), "skip-fallback"
    return text, "unchanged"


rng = random.Random(SEED)
files = sorted(glob.glob(os.path.join(RAW_DIR, "*.txt")))
assert files, f"No .txt files found in {RAW_DIR}"
print("contract files found:", len(files))

rows, dropped, methods = [], 0, Counter()
for f in files:
    with open(f, encoding="utf-8", errors="ignore") as fh:
        text = clean_text(fh.read())
    text, how = cut_preamble(text)
    text = LEADING_ENUM.sub("", text, count=1)
    methods[how] += 1
    # Drop contracts that still open with SEC confidentiality boilerplate
    if CONF_FLAG.search(" ".join(text.split()[:60])):
        dropped += 1
        continue
    n = rng.randint(MIN_TRUNC, MAX_WORDS) if RANDOMIZE_LENGTH else MAX_WORDS
    text = " ".join(text.split()[:n])
    rows.append({"text": text, "file": os.path.basename(f)})

print("preamble removed by:", dict(methods))
print("dropped (SEC confidentiality boilerplate):", dropped)

df = pd.DataFrame(rows)
df = df[df["text"].str.split().str.len() >= MIN_WORDS]
df = df.drop_duplicates(subset="text")

out = pd.DataFrame({"text": df["text"], "label": "Contract", "source": "cuad"})
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
out.to_csv(OUT_PATH, index=False, encoding="utf-8")

os.makedirs(os.path.dirname(EXTRA_PATH), exist_ok=True)
df[["file", "text"]].to_csv(EXTRA_PATH, index=False, encoding="utf-8")

print("result:", out.shape)
print("average length (words):", round(out["text"].str.split().str.len().mean(), 1))

print("\n--- leftover patterns (should be close to 0) ---")
t = out["text"]
first12 = t.str.split().str[:12].str.join(" ")
print("'agreement' in the first 12 words:", first12.str.contains(r"(?i)agreement").sum(), "of", len(t))
print("starts with 3+ ALL-CAPS words:", t.str.match(r"^(?:[A-Z][A-Z&.,'-]+\s+){3,}").sum())
print("SEC-header leftovers:", t.str.contains(r"(?i)information in this exhibit|confidential treatment|redacted").sum())
print("XXXX runs:", t.str.contains(r"\bX{4,}\b").sum())

left = t[t.str.contains("Source:")]
print("Source: footers left:", len(left))
for s in left.head(5):
    i = s.index("Source:")
    print("   ", repr(s[max(0, i - 40): i + 150]))

print("\n--- 8 examples (look at how each one starts) ---")
for s in out["text"].sample(8, random_state=1):
    print("-", s[:200], "\n")

print("starts with a digit:", t.str.match(r"^\s*\d").sum())