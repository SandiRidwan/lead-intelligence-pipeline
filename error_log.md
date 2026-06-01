# Error Log — Lead Intelligence Pipeline

**Project:** P22 — Lead Intelligence Pipeline  
**Run Date:** 1 Jun 2026  
**Author:** Sandi Ridwan

---

## Summary

| Category | Count | Disposition |
|---|---|---|
| Duplicates removed | 1 | Dropped — kept first occurrence |
| Noise messages filtered | 3 | Dropped — below quality threshold |
| Unmapped territory | 1 | Routed to fallback global rep |
| LLM failures | 0 | N/A |
| Pipeline crashes | 0 | N/A |

---

## Detail Log

### ERR-001 — Duplicate Lead
**Lead:** Acme Logistics Inc (`john.smith@acmelogistics.com`)  
**What happened:** Exact duplicate row appeared at position 7 in CSV (identical company, website, email, message).  
**Root cause:** Upstream form submission or data entry error.  
**Handling:** MD5 hash dedup in `ingest.py` detected match — second row dropped, first row kept.  
**Impact:** None. Lead processed correctly from first occurrence.

---

### ERR-002 — Noise Message: "Following"
**Lead:** PulseMedia Agency (`social@pulsemedia.com`)  
**What happened:** Message field contained only the word "Following" — 1 word, below 5-word threshold.  
**Root cause:** Social media-style engagement response submitted as a lead form entry.  
**Handling:** `is_noise()` filter in `ingest.py` — matched word count < 5 AND matched noise phrase list.  
**Impact:** Lead dropped before enrichment. Not in output CSV. Saves 1 Groq API call.

---

### ERR-003 — Noise Message: "check inbox"
**Lead:** RedRock Mining (`info@redrockmin.com`)  
**What happened:** Message field contained "check inbox" — matched noise phrase pattern.  
**Root cause:** Likely a reply to a previous outreach, not an inbound inquiry.  
**Handling:** `is_noise()` filter — exact phrase match in `NOISE_PHRASES` list.  
**Impact:** Lead dropped before enrichment. Not in output CSV.

---

### ERR-004 — Noise Message: "Interested in your platform"
**Lead:** GreenField Agriculture (`contact@greenfield-ag.com`)  
**What happened:** Message contained the word "interested" — matched noise phrase pattern. Message was also only 4 words.  
**Root cause:** Low-effort form submission with no specific pain point.  
**Handling:** `is_noise()` filter — matched both word count < 5 AND noise phrase "interested".  
**Impact:** Lead dropped before enrichment. Not in output CSV.

---

### ERR-005 — Unmapped Territory: Singapore
**Lead:** GlobalTrade Partners (`partner@globaltrade.com`)  
**What happened:** Lead country is Singapore — not covered by any of the 5 defined sales territories (Northeast US, West Coast US, Central US, Canada, UK & Europe).  
**Root cause:** Territory config intentionally has gaps for Asia-Pacific region.  
**Handling:** `geoRoute.py` exhausted city match and country match, fell through to `fallback_rep` (Sarah Global, global@company.com).  
**Flag:** `routing_method: fallback_unmapped`, `assigned_region: Unmapped: Singapore`  
**Impact:** Lead still processed, enriched, scored (86 — HIGH PRIORITY), and Slack alert sent to Sarah Global. No lead dropped.  
**Recommendation:** Add Asia-Pacific territory rep to `config/territory.json` if Singapore/SEA leads increase in volume.

---

## What Did NOT Fail

| Component | Status | Notes |
|---|---|---|
| Groq API enrichment | ✅ 16/16 | Zero LLM failures across all 16 leads |
| Geo-routing | ✅ 16/16 | All leads assigned — 15 to named reps, 1 to fallback |
| Scoring | ✅ 16/16 | All scores calculated correctly |
| Slack alerts | ✅ 11/11 | All HIGH PRIORITY leads notified |
| CSV output | ✅ 16 rows | All fields populated |
| Pipeline orchestration | ✅ | Completed in 22s, exit code 0 |

---

## Model Deprecation — Resolved During Build

**Issue:** Initial model `llama3-70b-8192` returned HTTP 400 `model_decommissioned`.  
**Detection:** Immediately visible in logs on first run.  
**Fix:** Updated model string to `llama-3.3-70b-versatile` in `enrich.py`.  
**Time to fix:** < 2 minutes.  
**Lesson:** Always check Groq deprecation page before locking a model string in production. Consider externalizing model name to `.env` for easier future updates.

---

*Log version 1.0 — Sandi Ridwan — 1 Jun 2026*
