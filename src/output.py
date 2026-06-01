import os
import logging
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def build_output_rows(df, enriched_list, scored_list, routed_list):
    rows = []
    for i, (_, lead) in enumerate(df.iterrows()):
        enriched = enriched_list[i]
        scored = scored_list[i]
        routed = routed_list[i]
        row = {
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
            'company_name': lead.get('company_name', ''),
            'website': lead.get('website', ''),
            'country': lead.get('country', ''),
            'city': lead.get('city', ''),
            'contact_email': lead.get('contact_email', ''),
            'message': lead.get('message', ''),
            'industry': enriched.get('industry', ''),
            'company_size_tier': enriched.get('company_size_tier', ''),
            'icp_score': enriched.get('icp_score', 0),
            'intent_signals': ', '.join(enriched.get('intent_signals', [])),
            'summary': enriched.get('summary', ''),
            'assigned_rep': routed.get('assigned_rep', ''),
            'assigned_rep_email': routed.get('assigned_rep_email', ''),
            'assigned_region': routed.get('assigned_region', ''),
            'routing_method': routed.get('routing_method', ''),
            'final_score': scored.get('final_score', 0),
            'priority_flag': scored.get('priority_flag', 'NORMAL'),
            'lead_hash': lead.get('lead_hash', '')
        }
        rows.append(row)
    return rows

def save_to_csv(rows, output_path='logs/output_leads.csv'):
    df_out = pd.DataFrame(rows)
    df_out.to_csv(output_path, index=False)
    logger.info(f"Output saved to {output_path} ({len(rows)} rows)")
    return output_path

def save_to_google_sheet(rows, sheet_name='Lead Intelligence Output'):
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'config/google_credentials.json')
        if not os.path.exists(creds_path):
            logger.warning(f"Google credentials not found at {creds_path} - skipping Google Sheets")
            return False
        scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open(sheet_name).sheet1
        if not rows:
            return False
        headers = list(rows[0].keys())
        existing = sheet.get_all_values()
        if not existing:
            sheet.append_row(headers)
        for row in rows:
            sheet.append_row(list(row.values()))
        logger.info(f"Google Sheet updated: {len(rows)} rows written to '{sheet_name}'")
        return True
    except Exception as e:
        logger.error(f"Google Sheets error: {e}")
        return False

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
    rows = build_output_rows(df, enriched, scored, routed)
    path = save_to_csv(rows)
    print(f"\nOutput CSV saved: {path}")
    print(f"Total rows: {len(rows)}")
    high = sum(1 for r in rows if r['priority_flag'] == 'HIGH')
    print(f"HIGH PRIORITY: {high}")
    print(f"NORMAL: {len(rows) - high}")
