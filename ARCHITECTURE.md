# Architecture Document — Lead Intelligence & Territory Routing Pipeline

**Project:** P22 — Lead Intelligence Pipeline  
**Author:** Sandi Ridwan  
**Date:** 1 Jun 2026  
**Version:** 1.0

---

## 1. Problem Statement

A B2B SaaS company receives ~200 inbound leads/day from a web form. Each lead is manually reviewed, enriched, and routed to a sales rep — consuming 3–4 hours of daily effort and introducing routing inconsistencies.

**Goal:** Automate the entire pipeline end-to-end. Zero manual steps from CSV intake to sales rep notification.

---

## 2. High-Level Architecture

```
INPUT                PROCESS                          OUTPUT
──────               ───────                          ──────

leads.csv      ──►   [1] ingest.py                   
                         MD5 dedup                   
                         noise filter                 
                              │                       
                              ▼                       
                     [2] enrich.py                   
                         Groq LLM                    
                         industry / size /            
                         ICP score / summary          
                              │                       
                              ▼                       
                     [3] geoRoute.py                 
                         city → country               
                         → fallback                   
                              │                       
                              ▼                       
                     [4] score.py                    
                         weighted 0-100               
                         HIGH / NORMAL flag           
                              │                       
                    ┌─────────┴──────────┐           
                    ▼                    ▼            
             [5] notify.py        [5] output.py      
             Slack Block Kit      CSV + Google Sheet  
             HIGH PRIORITY only   all 16 leads        
```

---

## 3. Component Decisions

### 3.1 Ingestion — `ingest.py`

**Decision:** CSV polling (not webhook).  
**Reason:** Webhook requires a live server/endpoint. For this scope (portfolio + B2B SaaS intake), CSV polling is simpler to deploy, test, and hand off. Webhook can be added as a thin wrapper on top of the same `load_leads()` function without changing downstream logic.

**Deduplication method:** MD5 hash of `company_name + website + contact_email`.  
**Reason:** Email alone is too brittle (same company, different contact). Domain alone misses subsidiaries. Three-field composite gives best precision without over-engineering.

**Noise filter:** Regex + word count check before LLM call.  
**Reason:** Sending noise to LLM wastes API quota and money. Filter early — messages under 5 words or containing known spam phrases are dropped before enrichment.

---

### 3.2 LLM Enrichment — `enrich.py`

**Decision:** Groq API with `llama-3.3-70b-versatile`.  
**Reason:** Free tier, ~500ms per call, reliable structured JSON output. OpenAI GPT-4o would give marginally better accuracy but costs ~$0.01/call × 200 leads/day = $2/day = $730/year. For this use case, Groq's quality is sufficient at $0 cost.

**Temperature:** 0.1 (not 0).  
**Reason:** Temperature 0 can produce repetitive token loops on some models. 0.1 gives near-deterministic output while avoiding this artifact.

**Output enforcement:** System prompt explicitly bans markdown, explanation, and preamble. Every response goes through `json.loads()` with 3-retry backoff.  
**Reason:** LLMs occasionally wrap JSON in markdown fences or add a leading sentence. The strip + retry loop handles this gracefully without crashing the pipeline.

**Fallback on total failure:** Returns default dict with `icp_score: 0` and `summary: "manual review needed"`.  
**Reason:** One bad LLM response should not stop 15 other leads from being processed. Pipeline continues; failed lead is flagged for human review in output CSV.

---

### 3.3 Geo-Routing — `geoRoute.py`

**Decision:** Static JSON config (not live geocoding API like Google Maps or Nominatim).  
**Reason:** Live geocoding adds latency, API cost, and a new failure point. For a defined sales territory (5 reps, fixed regions), a static JSON config is faster, cheaper, and more predictable. Territory changes are a config update, not a code change.

**Routing priority:** City match → Country match → Fallback global rep.  
**Reason:** City-first prevents false country-level assignment. A lead from Denver routes to Lisa Chen (West Coast), not Emma Williams (Canada), even though both share `United States`. City specificity is preserved when available.

**Missing city handling:** Skip city lookup entirely, go straight to country match.  
**Reason:** Raising an error on missing city would drop valid leads. Country-level routing is still useful and accurate for the majority of cases.

**Unmapped territories:** All leads outside defined territories (Singapore, Brazil, etc.) go to a named fallback rep (`Sarah Global`) with `routing_method: fallback_unmapped` flag.  
**Reason:** No lead is silently dropped. The fallback rep flag makes it visible in the output CSV for manual territory expansion later.

---

### 3.4 Scoring — `score.py`

**Decision:** Weighted formula instead of pure LLM score.  
**Reason:** LLM ICP score alone is not auditable. A sales rep cannot understand why Acme scored 90 vs 70. The decomposed formula — ICP × 0.75 + size_bonus + intent_bonus — makes every score explainable and adjustable without retraining.

**Weights chosen:**

| Component | Weight | Rationale |
|---|---|---|
| ICP score | 75% | LLM's holistic pain-point assessment is the primary signal |
| Company size | +0 to +15 | Enterprise deals close larger — size is a strong revenue predictor |
| Intent signals | +0 to +10 | Specific signals (FDA compliance, SOC2, cost reduction) indicate genuine intent |

**HIGH PRIORITY threshold:** 75 (configurable via `.env`).  
**Reason:** Hardcoded thresholds become stale as pipeline is tuned. Externalized to `.env` so the sales team can adjust without touching code.

---

### 3.5 Notifications — `notify.py`

**Decision:** Slack Incoming Webhooks with Block Kit format.  
**Reason:** Webhooks require no OAuth flow, no token refresh, no bot permissions — just a URL. Block Kit renders structured cards (not plain text) with Company, Location, Rep, Score, Summary, and Intent Signals in a scannable format on both desktop and mobile Slack.

**Scope:** HIGH PRIORITY only (score ≥ 75).  
**Reason:** Alerting on all 16 leads would flood the channel and train reps to ignore alerts. Signal-to-noise ratio matters more than volume.

---

### 3.6 Output — `output.py`

**Decision:** CSV primary output, Google Sheets optional.  
**Reason:** CSV works everywhere, requires zero credentials, and is immediately reviewable in VS Code or Excel. Google Sheets is wired in but gated behind a service account credentials check — if credentials are absent, pipeline skips Sheets and saves CSV without failing.

**Timestamp format:** ISO 8601 UTC (`2026-06-01 09:08:43 UTC`).  
**Reason:** Unambiguous across timezones. Critical for a pipeline that may run on a server in a different timezone than the sales team.

---

### 3.7 Orchestration — `pipeline.py`

**Decision:** Single orchestrator script with dual logging (file + stdout).  
**Reason:** Every pipeline run produces a timestamped log file in `logs/`. This gives a full audit trail — when did it run, how many leads, what failed, how long it took — without requiring a separate monitoring tool.

**Error handling:** `try/except` wraps the entire pipeline. On fatal error, logs the full traceback and exits with code 1 (detectable by cron/scheduler).

---

## 4. Tradeoffs & What Was Left Out

| Decision | Tradeoff | Future path |
|---|---|---|
| CSV ingestion (not webhook) | Simpler but requires manual file drop | Add FastAPI webhook endpoint that writes to same CSV |
| Static territory JSON (not geocoding) | Fast and free but requires manual config updates | Add Nominatim geocoding as fallback for unmapped cities |
| No database (CSV output only) | Simple but not queryable at scale | Add SQLite or Supabase for incremental run history |
| No deduplication across runs | Each run is independent | Add lead_hash lookup against persistent store |
| Groq free tier | Fast and free but rate-limited at scale | Add OpenAI as fallback when Groq rate limit hit |
| Google Sheets optional | Reduces complexity for portfolio | Add service account setup guide for production use |

---

## 5. Scalability Path

Current pipeline handles ~20 leads in 22 seconds. At 200 leads/day:

```
200 leads × 0.5s per Groq call = ~100s enrichment time
+ dedup / routing / scoring    = ~5s
+ Slack alerts (HIGH only)     = ~20s (est. 50 high priority)
─────────────────────────────────────────
Total estimated runtime at 200 leads/day: ~2 minutes
```

No architectural changes needed up to ~500 leads/day. Above that:
- Batch Groq calls with `asyncio` for parallel enrichment
- Move output to Supabase for queryable history
- Add webhook trigger instead of manual CSV drop

---

## 6. File Dependency Map

```
pipeline.py
    ├── ingest.py          (no internal deps)
    ├── enrich.py          (no internal deps)
    ├── geoRoute.py        (no internal deps)
    ├── score.py           (no internal deps)
    ├── notify.py          (no internal deps)
    └── output.py          (no internal deps)

All modules are independently testable.
pipeline.py is the only file that imports from other src/ modules.
```

---

## 7. Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GROQ_API_KEY` | ✅ | — | Groq API authentication |
| `SLACK_WEBHOOK_URL` | ✅ | — | Slack channel webhook |
| `LEADS_CSV_PATH` | ❌ | `data/leads.csv` | Input file path |
| `TERRITORY_CONFIG_PATH` | ❌ | `config/territory.json` | Territory routing config |
| `HIGH_PRIORITY_THRESHOLD` | ❌ | `75` | Score threshold for alerts |

---

*Document version 1.0 — Sandi Ridwan — 1 Jun 2026*
