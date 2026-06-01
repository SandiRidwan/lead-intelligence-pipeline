import logging
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)

SIZE_WEIGHT = {
    'Enterprise': 15,
    'Mid-Market': 8,
    'SMB': 0,
    'Unknown': 0
}

def calculate_score(enriched):
    icp = enriched.get('icp_score', 0)
    if not isinstance(icp, (int, float)): icp = 0
    icp = max(0, min(100, icp))

    size_tier = enriched.get('company_size_tier', 'Unknown')
    size_bonus = SIZE_WEIGHT.get(size_tier, 0)

    intent_signals = enriched.get('intent_signals', [])
    intent_bonus = min(len(intent_signals) * 2, 10)

    raw_score = icp * 0.75 + size_bonus + intent_bonus
    final_score = round(min(100, max(0, raw_score)))

    threshold = int(os.getenv('HIGH_PRIORITY_THRESHOLD', 75))
    is_high_priority = final_score >= threshold

    return {
        'final_score': final_score,
        'icp_score': icp,
        'size_bonus': size_bonus,
        'intent_bonus': intent_bonus,
        'is_high_priority': is_high_priority,
        'priority_flag': 'HIGH' if is_high_priority else 'NORMAL'
    }

def score_all(enriched_list):
    results = []
    high_count = 0
    for enriched in enriched_list:
        scored = calculate_score(enriched)
        results.append(scored)
        if scored['is_high_priority']:
            high_count += 1
    logger.info(f"Scoring complete: {len(results)} leads, {high_count} HIGH PRIORITY")
    return results

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    from src.ingest import load_leads
    from src.enrich import enrich_all
    import os
    csv_path = os.getenv("LEADS_CSV_PATH", "data/leads.csv")
    df = load_leads(csv_path)
    enriched = enrich_all(df)
    scores = score_all(enriched)
    print(f"\n{'Company':<25} {'ICP':>4} {'Size Bonus':>10} {'Intent':>7} {'Final':>6} {'Flag':<8}")
    print("-" * 65)
    for i, s in enumerate(scores):
        company = df.iloc[i]['company_name'][:24]
        print(f"{company:<25} {s['icp_score']:>4} {s['size_bonus']:>10} {s['intent_bonus']:>7} {s['final_score']:>6} {s['priority_flag']:<8}")
