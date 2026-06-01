<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Orbitron&weight=900&size=46&duration=3000&pause=1000&color=00FFFF&center=true&vCenter=true&width=800&height=90&lines=SANDI+RIDWAN" alt="Sandi Ridwan" />

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=16&duration=2500&pause=800&color=7EB8D4&center=true&vCenter=true&width=750&lines=Data+Automation+Engineer+%7C+AI+Pipeline+Builder;Lead+Intelligence+Pipeline+%E2%80%94+20+Leads+Enriched+in+22s;Groq+LLM+%7C+Geo-Routing+%7C+Slack+Alerts+%7C+Scoring+Engine" alt="Subtitle" />

<br/><br/>

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Groq](https://img.shields.io/badge/Groq-llama--3.3--70b-F55036?style=for-the-badge)](https://groq.com)
[![Slack](https://img.shields.io/badge/Slack-Block%20Kit%20Alerts-4A154B?style=for-the-badge&logo=slack&logoColor=white)](https://slack.com)
[![pandas](https://img.shields.io/badge/pandas-Data%20Pipeline-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

<div align="center">

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│          LEAD INTELLIGENCE & TERRITORY ROUTING PIPELINE              │
│          End-to-End B2B Lead Enrichment · Scoring · Routing          │
│                                                                      │
│   20 raw leads  ──►  16 clean  ──►  LLM enriched  ──►  11 alerts    │
│   Groq API  ·  Geo-Routing  ·  Slack Block Kit  ·  22s runtime      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

</div>

---

## 📹 Demo

<div align="center">
  <a href="https://youtube.com/watch?v=YOUR_VIDEO_ID">
    <img src="thumbnail.png" width="860" alt="Watch full demo on YouTube" />
  </a>
  <br/>
  <sub><i>Click to watch — pipeline run, Slack alerts, CSV output walkthrough</i></sub>
</div>

<br/>

<div align="center">
  <video src="https://github.com/user-attachments/assets/YOUR_ASSET_ID" 
         width="860" 
         controls 
         autoplay 
         loop 
         muted>
  </video>
</div>

---

## ⚡ Overview

An end-to-end automated B2B lead intelligence pipeline that eliminates 3–4 hours of daily manual lead processing. Raw leads go in — enriched, scored, routed, and alerted leads come out.

<div align="center">

| Metric | Value |
|:---|---:|
| Raw leads input | **20** |
| Duplicates removed | **1** |
| Noise messages filtered | **3** |
| Clean leads processed | **16** |
| HIGH PRIORITY leads | **11** |
| Slack alerts sent | **11** |
| Pipeline runtime | **~22 seconds** |
| LLM calls (Groq) | **16** |
| Cost | **$0 (free tier)** |

</div>

---

## 🧠 Pipeline Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  leads.csv  │────►│  ingest.py  │────►│  enrich.py  │
│  (20 rows)  │     │  MD5 dedup  │     │  Groq LLM   │
└─────────────┘     │  noise filt │     │  ICP score  │
                    └─────────────┘     └──────┬──────┘
                                               │
                    ┌─────────────┐     ┌──────▼──────┐
                    │  output.py  │◄────│  score.py   │
                    │  CSV + Sheet│     │  0-100 score│
                    └──────┬──────┘     └──────┬──────┘
                           │                   │
                    ┌──────▼──────┐     ┌──────▼──────┐
                    │  notify.py  │     │ geoRoute.py │
                    │  Slack alert│     │ city→country│
                    └─────────────┘     │ →fallback   │
                                        └─────────────┘
```

**Orchestrated by `pipeline.py` — one command runs all 5 stages with full logging.**

---

## 🏗️ Why This Pipeline Is Non-Trivial

> *"Most lead pipelines are just CSV → spreadsheet. This one thinks."*

Three problems make this harder than it looks:

### 1. LLM Output Must Be Deterministic

A sales pipeline cannot tolerate hallucinated JSON or inconsistent scoring. The LLM is prompted with a strict system instruction that enforces exact output schema — and every response goes through a 3-retry parse loop with fallback defaults.

```python
# enrich.py — structured output enforcement
SYSTEM_PROMPT = """Return ONLY a valid JSON object. No markdown, no explanation.
Required keys: industry, company_size_tier, icp_score (0-100), intent_signals, summary"""

for attempt in range(3):
    try:
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)   # ← fails here if LLM misbehaves
    except json.JSONDecodeError:
        time.sleep(1)            # ← retry with backoff
```

### 2. Geo-Routing Must Handle Gaps

Territory configs in the real world always have gaps — unmapped cities, missing location data, international leads. This pipeline handles all three explicitly, not with a crash.

```
City match     →  direct assign (highest precision)
Country match  →  regional assign (fallback tier 1)
No match       →  fallback global rep (no lead dropped)
Missing city   →  skip city lookup, go straight to country
```

### 3. Scoring Must Be Explainable

A black-box score is useless to a sales rep. Every final score is decomposed into three auditable components:

```
final_score = (icp_score × 0.75) + size_bonus + intent_bonus

icp_score   = LLM assessment of pain point + urgency (0-100)
size_bonus  = Enterprise:15 | Mid-Market:8 | SMB:0
intent_bonus = min(signal_count × 2, 10)
```

---

## 🧩 Technical Highlights

### Structured LLM Output via Groq

```python
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ],
    temperature=0.1,    # ← low temp for consistent JSON
    max_tokens=300
)
```

**Temperature 0.1** — not 0. Pure 0 can cause repetition artifacts. 0.1 gives deterministic-enough output while avoiding token loops.

---

### MD5 Hash Deduplication

```python
def make_hash(row):
    key = (str(row["company_name"]).lower().strip() + "_" +
           str(row["website"]).lower().strip() + "_" +
           str(row["contact_email"]).lower().strip())
    return hashlib.md5(key.encode()).hexdigest()

df["lead_hash"] = df.apply(make_hash, axis=1)
df = df.drop_duplicates(subset=["lead_hash"], keep="first")
```

Hash is written to output CSV — enables incremental dedup across pipeline runs without loading full history into memory.

---

### City-First Geo-Routing

```python
def route_lead(lead, territory_config):
    # Priority 1: exact city match
    for rep in territories:
        if city.lower() in [c.lower() for c in rep["cities"]]:
            return assign(rep, method="city_match")

    # Priority 2: country fallback
    for rep in territories:
        if country.lower() in [c.lower() for c in rep["countries"]]:
            return assign(rep, method="country_match")

    # Priority 3: global fallback — no lead dropped
    return assign(fallback_rep, method="fallback_unmapped")
```

City-first prevents false assignment — "Denver" (US) won't accidentally route to a Canada rep just because Colorado isn't explicitly in the city list.

---

### Slack Block Kit Alerts

```python
message = {
    "blocks": [
        {"type": "header", "text": {"type": "plain_text",
            "text": f"HIGH PRIORITY LEAD - Score {score}/100"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*Company:*\n{company}"},
            {"type": "mrkdwn", "text": f"*Assigned Rep:*\n{rep}"},
            ...
        ]},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*Summary:*\n{summary}"}}
    ]
}
```

Block Kit (not plain text) — structured card format that renders cleanly on mobile and desktop Slack.

---

## 📁 Project Structure

```
lead-intelligence-pipeline/
│
├── src/
│   ├── ingest.py       ← CSV ingestion, MD5 dedup, noise filter
│   ├── enrich.py       ← Groq LLM enrichment + 3-retry logic
│   ├── geoRoute.py     ← Territory routing (city → country → fallback)
│   ├── score.py        ← Weighted scoring formula 0-100
│   ├── notify.py       ← Slack Block Kit alerts
│   ├── output.py       ← CSV + Google Sheets output
│   └── pipeline.py     ← Main orchestrator + dual logging
│
├── config/
│   └── territory.json  ← 5 sales reps + fallback global rep
│
├── data/
│   └── leads.csv       ← Input: company, website, country, city, message, email
│
├── logs/
│   ├── output_leads.csv          ← Enriched output with all 19 fields
│   └── pipeline_YYYYMMDD_HHMMSS.log  ← Per-run audit log
│
├── .env                ← API keys — never commit
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

**1. Clone dan setup:**
```bash
git clone https://github.com/sandiridwan/lead-intelligence-pipeline
cd lead-intelligence-pipeline
python -m venv venv
venv\Scripts\activate        # Windows
pip install pandas groq slack-sdk gspread google-auth python-dotenv
```

**2. Isi `.env`:**
```
GROQ_API_KEY=your_groq_api_key
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
LEADS_CSV_PATH=data/leads.csv
TERRITORY_CONFIG_PATH=config/territory.json
HIGH_PRIORITY_THRESHOLD=75
```

**3. Siapkan leads di `data/leads.csv`:**
```
company_name, website, country, city, message, contact_email
```

**4. Jalankan:**
```bash
python src/pipeline.py
```

---

## 🗂️ Output Fields

**19 fields per lead — all original + enrichment + routing + scoring:**

```
timestamp          company_name       website            country
city               contact_email      message            industry
company_size_tier  icp_score          intent_signals     summary
assigned_rep       assigned_rep_email assigned_region    routing_method
final_score        priority_flag      lead_hash
```

---

## ⚠️ Edge Cases Handled

| Case | Handling |
|:-----|:---------|
| Duplicate leads | MD5 hash dedup — keep first occurrence |
| Noise messages (`"following"`, `"check inbox"`, <5 words) | Filtered before enrichment — never sent to LLM |
| Missing city | Skip city lookup, route by country |
| Missing city + country | Assign to fallback global rep |
| Unmapped territory (Singapore, etc.) | Fallback rep + `routing_method: fallback_unmapped` flag |
| LLM JSON parse failure | 3 retries with 1–2s backoff |
| LLM total failure | Graceful fallback: score 0, `"manual review needed"` |
| Slack webhook missing | Warning log — pipeline continues |
| Google Sheets credentials missing | Skip with warning — CSV still saved |

---

## 👤 Author

<div align="center">

**Sandi Ridwan**
*Data Automation Engineer & AI Pipeline Builder — Palu, Indonesia*

[![Upwork](https://img.shields.io/badge/Upwork-Hire%20Me-6FDA44?style=for-the-badge&logo=upwork&logoColor=white)](https://upwork.com/freelancers/sandiridwan)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/sandi-ridwan)
[![GitHub](https://img.shields.io/badge/GitHub-Portfolio-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/sandiridwan)

<br/>

<sub>Built with precision. Automated with intent.</sub>

</div>
