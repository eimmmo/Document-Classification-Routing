import sys
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ALLOWED_LABELS = {"Complaint", "Contract", "Service Request"}
KEEP_COLUMNS = ["text", "label", "source"]
MIN_WORDS, MAX_WORDS = 40, 250
TRUNCATE_TO = 70


def load_one(path):
    df = pd.read_csv(path, encoding="utf-8")
    missing = [c for c in KEEP_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    # drop any extra column (for example: product)
    return df[KEEP_COLUMNS].copy()

def drop_near_duplicates(df, threshold=0.8):
    vec = TfidfVectorizer(stop_words="english")
    sim = cosine_similarity(vec.fit_transform(df["text"]))
    np.fill_diagonal(sim, 0)
    keep, dropped = [], set()
    for i in range(len(df)):
        if i in dropped:
            continue
        keep.append(i)
        for j in np.where(sim[i] >= threshold)[0]:
            if j > i:
                dropped.add(j)
    return df.iloc[keep]
def main(paths, out_path="dataset.csv"):
    frames = [load_one(p) for p in paths]
    df = pd.concat(frames, ignore_index=True)
    print("rows after concat:", len(df))

    # label names must match exactly
    bad = set(df["label"].unique()) - ALLOWED_LABELS
    if bad:
        raise ValueError(f"unexpected labels: {bad}")

    # rule checks
    df = df.dropna(subset=["text"])
    df["text"] = df["text"].str.replace(r"\\n", " ", regex=True)
    df["text"] = df["text"].apply(lambda t: " ".join(t.split()))
    df = df[~df["text"].str.contains("XXXX", na=False)]
    words = df["text"].str.split().str.len()
    df = df[(words >= MIN_WORDS) & (words <= MAX_WORDS)]
    df["text"] = df["text"].apply(lambda t: " ".join(t.split()[:TRUNCATE_TO]))
    print("after truncation to", TRUNCATE_TO, "words:", len(df))

    # exact duplicates
    before = len(df)
    df = df.drop_duplicates(subset=["text"])
    before = len(df)
    df = drop_near_duplicates(df)
    print("near duplicates removed:", before - len(df))
    print("exact duplicates removed:", before - len(df))

    df = df.reset_index(drop=True)
    df.to_csv(out_path, index=False, encoding="utf-8")
    print("rows saved:", len(df))
    print(df["label"].value_counts())


if __name__ == "__main__":
    default_files = ["complaints.csv", "contracts.csv"]
    files = sys.argv[1:] if len(sys.argv) > 1 else default_files
    main(files)