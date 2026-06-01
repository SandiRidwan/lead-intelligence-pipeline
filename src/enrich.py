import os
import json
import time
import logging
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a B2B sales intelligence analyst. Analyze the company info and message provided, then return ONLY a valid JSON object with no extra text, no markdown, no explanation.

Required JSON format:
{
  "industry": "string",
  "company_size_tier": "SMB or Mid-Market or Enterprise",
  "icp_score": integer 0-100,
  "intent_signals": ["signal1", "signal2"],
  "summary": "one sentence for sales rep"
}

Scoring guide:
- 80-100: Clear pain point, large company, specific metrics, urgent need
- 60-79: Good fit, some specifics, moderate urgency
- 40-59: Vague message, small company, unclear need
- 0-39: Very vague, no clear pain point"""

def enrich_lead(lead):
    prompt = f"Company: {lead.get('company_name','')}\nWebsite: {lead.get('website','')}\nCountry: {lead.get('country','')}\nCity: {lead.get('city','')}\nMessage: {lead.get('message','')}\n\nReturn JSON only."
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json","").replace("```","").strip()
            enriched = json.loads(raw)
            for key in ["industry","company_size_tier","icp_score","intent_signals","summary"]:
                if key not in enriched: enriched[key] = None
            return enriched
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error attempt {attempt+1}: {e}")
            time.sleep(1)
        except Exception as e:
            logger.warning(f"API error attempt {attempt+1}: {e}")
            time.sleep(2)
    logger.error(f"Failed to enrich: {lead.get('company_name')}")
    return {"industry":"Unknown","company_size_tier":"Unknown","icp_score":0,"intent_signals":[],"summary":"Enrichment failed - manual review needed"}

def enrich_all(df):
    results = []
    total = len(df)
    for i, row in df.iterrows():
        logger.info(f"Enriching {i+1}/{total}: {row['company_name']}")
        enriched = enrich_lead(row.to_dict())
        results.append(enriched)
        time.sleep(0.5)
    return results

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    from src.ingest import load_leads
    csv_path = os.getenv("LEADS_CSV_PATH", "data/leads.csv")
    df = load_leads(csv_path)
    results = enrich_all(df)
    for i, r in enumerate(results):
        print(f"--- {df.iloc[i]['company_name']} ---")
        print(json.dumps(r, indent=2))
        print()
