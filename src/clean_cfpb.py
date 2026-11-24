"""Build data/processed/complaints.csv from the CFPB narratives archive.

Source: CFPB Consumer Complaint Database Narratives Archive (FOIA Reading Room).
Since Aug 14, 2026 the CFPB no longer publishes narratives in the public
database, so the data comes from the archive:
https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/
File used: CCDB Export July 2026 (unzip it, then set RAW_PATH below).

Run from the repo root:  python src/clean_cfpb.py
"""
import os
import re
import pandas as pd

# ====== Settings ======
RAW_PATH = r"E:\CCDB_Export_20_July_2026\CCDB_Export_20_July_2026.csv"  
OUT_PATH = "data/processed/complaints.csv"
PRODUCTS = [
    "Credit card",
    "Checking or savings account",
    "Debt collection",
    "Mortgage",
    "Student loan",
]
PER_PRODUCT = 200
MIN_WORDS, MAX_WORDS = 10, 250
SEED = 42
# ======================


def clean_text(t):
    t = str(t)
    t = re.sub(r"X{2,}", " ", t)                     
    t = re.sub(r"<?year>", " ", t)                    
    t = re.sub(r"\s*/\s*/\s*", " ", t)                
    t = re.sub(r"[{}<>]", "", t)                      
    t = re.sub(r"\s+#\s*", " ", t)                    
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)            
    t = re.sub(r"([,.;:])(?:\s*[,.;:])+", r"\1", t)   

    
    t = re.sub(r"\(\s+", "(", t)
    t = re.sub(r"\s+\)", ")", t)

    
    t = re.sub(r"(\w)\s+(n't)\b", r"\1\2", t)
    t = re.sub(r"(\w)\s+('(?:s|re|ve|ll|d|m))\b", r"\1\2", t)

    
    t = t.replace("``", '"').replace("''", '"').replace("`", "'")
    t = re.sub(r'"\s+([^"]+?)\s*"', r'"\1"', t)

    t = re.sub(r"\s+", " ", t).strip()
    return t


df = pd.read_csv(
    RAW_PATH,
    usecols=["Product", "Consumer complaint narrative"],
    low_memory=False,
)
print("raw rows:", len(df))


df = df[df["Product"].isin(PRODUCTS)]
df = df.dropna(subset=["Consumer complaint narrative"]).copy()
print("after filtering products and text:", len(df))


df["text"] = df["Consumer complaint narrative"].apply(clean_text)
df["text"] = df["text"].apply(lambda s: " ".join(s.split()[:MAX_WORDS]))


df = df[df["text"].str.split().str.len() >= MIN_WORDS]
df = df.drop_duplicates(subset="text")
print("after exact-duplicate removal:", len(df))


df["_prefix"] = df["text"].str[:120]
df = df.drop_duplicates(subset="_prefix").drop(columns="_prefix")
print("after near-duplicate removal:", len(df))

print("\navailable per product after cleaning:")
print(df["Product"].value_counts())


parts = []
for prod, g in df.groupby("Product"):
    parts.append(g.sample(n=min(len(g), PER_PRODUCT), random_state=SEED))
df = pd.concat(parts)


out = pd.DataFrame({
    "text": df["text"],
    "label": "Complaint",
    "source": "cfpb",
    "product": df["Product"],
})
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
out.to_csv(OUT_PATH, index=False)

print("\nresult:", out.shape)
print(out["product"].value_counts())
print("average length (words):", round(out["text"].str.split().str.len().mean(), 1))

print("\n--- leftover patterns ---")
for pat in [r"\{", r"year>", r"/\s*/", r"\s,", r"\(\s|\s\)", r"''|`"]:
    print(pat, "->", out["text"].str.contains(pat).sum())