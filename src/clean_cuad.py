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
RAW_DIR = r"E:\CUAD\CUAD_v1\CUAD_v1\full_contract_txt"  
OUT_PATH = "data/processed/contracts.csv"
EXTRA_PATH = "data/extra/cuad_files.csv"   
MIN_WORDS, MAX_WORDS = 10, 250
RANDOMIZE_LENGTH = True    
MIN_TRUNC = 50
SEARCH_WORDS = 600         
PREAMBLE_SKIP = 80        
SEED = 42
# ======================

LEAD_NUMBERS = re.compile(r"^\s*(?:\d+(?:\.\d+)*\.?\s+){2,}")      
LEAD_SINGLE = re.compile(r"^\s*\d{1,2}\s+(?=[A-Za-z])")            
LEAD_EXHIBIT = re.compile(r"(?i)^\s*exhibits?\s+\S+\s*=?\s*")       
CONF_FLAG = re.compile(
    r"(?i)redacted|confidential treatment|confidentiality request|"
    r"(?:has|have) been omitted|omits the information|\{\*+\}|c\.f\.r\."
)
AGREE_AS_FOLLOWS = re.compile(r"(?i)\bagree[sd]?\s+(?:as\s+follows|to\s+the\s+following)\s*[:.;,]?")
NOW_THEREFORE = re.compile(r"(?i)\bnow,?\s+therefore\b")


def clean_text(t):
    t = re.sub(r"\[[\s*]+\]", " ", t)                                  
    t = re.sub(r"(?im)^\s*page\s+\d+(\s+of\s+\d+)?\s*$", " ", t)       
    t = re.sub(r"[_=\-]{4,}", " ", t)                                 
    t = re.sub(r"(?i)\(\s*execution\s+(?:version|copy)[^)]*\)", " ", t)
    t = re.sub(r"(?i)\bexecution\s+(?:version|copy)\b", " ", t)
    t = re.sub(r"\bX{4,}\b", " ", t)                                  
    t = re.sub(r"(?i)information\s+in\s+this\s+exhibit[^.]*\.", " ", t)
    t = re.sub(r"(?i)certain\s+(?:identified\s+)?information[^.]*?(?:omitted|redacted)[^.]*\.", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    for _ in range(4):                                                
        t = LEAD_NUMBERS.sub("", t)
        t = LEAD_SINGLE.sub("", t)
        t = LEAD_EXHIBIT.sub("", t)
    return t.strip()


def cut_preamble(text):
    """Remove the title and preamble. Returns (body, method)."""
    words = text.split()
    limit = len(" ".join(words[:SEARCH_WORDS]))   

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
    methods[how] += 1
    
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

print("\n--- 8 examples (look at how each one starts) ---")
for s in out["text"].sample(8, random_state=1):
    print("-", s[:200], "\n")