import pandas as pd
import hashlib
import logging
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

NOISE_PHRASES = ["following", "interested", "dm me", "check inbox", "pm sent", "please dm", "send me", "inbox me"]

def make_hash(row):
    key = str(row["company_name"]).lower().strip() + "_" + str(row["website"]).lower().strip() + "_" + str(row["contact_email"]).lower().strip()
    return hashlib.md5(key.encode()).hexdigest()

def is_noise(message):
    if not isinstance(message, str): return True
    msg = message.lower().strip()
    if len(msg.split()) < 5: return True
    for phrase in NOISE_PHRASES:
        if phrase in msg: return True
    return False

def normalize_fields(df):
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    for col in ["company_name", "website", "country", "city", "message", "contact_email"]:
        if col not in df.columns: df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()
    return df

def load_leads(csv_path):
    path = Path(csv_path)
    if not path.exists(): raise FileNotFoundError(f"CSV not found: {csv_path}")
    df = pd.read_csv(path)
    logger.info(f"Loaded {len(df)} raw rows from {csv_path}")
    df = normalize_fields(df)
    df["lead_hash"] = df.apply(make_hash, axis=1)
    before = len(df)
    df = df.drop_duplicates(subset=["lead_hash"], keep="first")
    dupes = before - len(df)
    if dupes > 0: logger.info(f"Removed {dupes} duplicate lead(s)")
    noise_mask = df["message"].apply(is_noise)
    noise_count = noise_mask.sum()
    df = df[~noise_mask].reset_index(drop=True)
    if noise_count > 0: logger.info(f"Filtered {noise_count} noise message(s)")
    logger.info(f"Clean leads ready for enrichment: {len(df)}")
    return df

if __name__ == "__main__":
    csv_path = os.getenv("LEADS_CSV_PATH", "data/leads.csv")
    df = load_leads(csv_path)
    print(df[["company_name", "city", "country", "message"]].to_string())
