import os
import logging
import urllib.request
import json
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def send_slack_alert(lead, enriched, scored, routed):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        logger.warning("No SLACK_WEBHOOK_URL set - skipping notification")
        return False

    score = scored.get('final_score', 0)
    company = lead.get('company_name', 'Unknown')
    city = lead.get('city', 'Unknown')
    country = lead.get('country', 'Unknown')
    rep = routed.get('assigned_rep', 'Unassigned')
    region = routed.get('assigned_region', '')
    industry = enriched.get('industry', 'Unknown')
    size = enriched.get('company_size_tier', 'Unknown')
    summary = enriched.get('summary', '')
    signals = enriched.get('intent_signals', [])

    message = {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"HIGH PRIORITY LEAD - Score {score}/100"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Company:*\n{company}"},
                    {"type": "mrkdwn", "text": f"*Location:*\n{city}, {country}"},
                    {"type": "mrkdwn", "text": f"*Industry:*\n{industry}"},
                    {"type": "mrkdwn", "text": f"*Size:*\n{size}"},
                    {"type": "mrkdwn", "text": f"*Assigned Rep:*\n{rep}"},
                    {"type": "mrkdwn", "text": f"*Region:*\n{region}"}
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Summary:*\n{summary}"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Intent Signals:* {', '.join(signals)}"}
            },
            {
                "type": "divider"
            }
        ]
    }

    try:
        data = json.dumps(message).encode('utf-8')
        req = urllib.request.Request(webhook_url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                logger.info(f"Slack alert sent: {company} (score {score})")
                return True
    except Exception as e:
        logger.error(f"Slack alert failed for {company}: {e}")
    return False

def notify_high_priority(df, enriched_list, scored_list, routed_list):
    sent = 0
    for i, scored in enumerate(scored_list):
        if scored.get('is_high_priority'):
            lead = df.iloc[i].to_dict()
            success = send_slack_alert(lead, enriched_list[i], scored, routed_list[i])
            if success:
                sent += 1
    logger.info(f"Slack notifications sent: {sent}")
    return sent

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    from src.ingest import load_leads
    from src.enrich import enrich_all
    from src.score import score_all
    from src.geoRoute import route_all
    import os
    csv_path = os.getenv("LEADS_CSV_PATH", "data/leads.csv")
    config_path = os.getenv("TERRITORY_CONFIG_PATH", "config/territory.json")
    df = load_leads(csv_path)
    enriched = enrich_all(df)
    scored = score_all(enriched)
    routed = route_all(df, config_path)
    sent = notify_high_priority(df, enriched, scored, routed)
    print(f"\nDone. {sent} Slack alerts sent.")
