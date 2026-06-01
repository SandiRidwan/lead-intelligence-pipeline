import json
import logging
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)

def load_territory(config_path):
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Territory config not found: {config_path}")
    with open(path, 'r') as f:
        return json.load(f)

def route_lead(lead, territory_config):
    city = str(lead.get('city', '')).strip()
    country = str(lead.get('country', '')).strip()
    territories = territory_config.get('territories', [])
    fallback = territory_config.get('fallback_rep', {})

    if not city and not country:
        logger.warning(f"No city/country for: {lead.get('company_name')} - assigned to fallback")
        return {
            'assigned_rep': fallback.get('rep_name', 'Unassigned'),
            'assigned_rep_email': fallback.get('rep_email', ''),
            'assigned_region': 'Unknown - Missing Location',
            'routing_method': 'fallback_missing_location'
        }

    for rep in territories:
        rep_cities = [c.lower() for c in rep.get('cities', [])]
        if city.lower() in rep_cities:
            logger.info(f"{lead.get('company_name')} -> {rep['rep_name']} (city match: {city})")
            return {
                'assigned_rep': rep['rep_name'],
                'assigned_rep_email': rep['rep_email'],
                'assigned_region': rep['region'],
                'routing_method': 'city_match'
            }

    for rep in territories:
        rep_countries = [c.lower() for c in rep.get('countries', [])]
        if country.lower() in rep_countries:
            logger.info(f"{lead.get('company_name')} -> {rep['rep_name']} (country match: {country})")
            return {
                'assigned_rep': rep['rep_name'],
                'assigned_rep_email': rep['rep_email'],
                'assigned_region': rep['region'],
                'routing_method': 'country_match'
            }

    logger.warning(f"{lead.get('company_name')} not in any territory ({country}/{city}) - fallback")
    return {
        'assigned_rep': fallback.get('rep_name', 'Unassigned'),
        'assigned_rep_email': fallback.get('rep_email', ''),
        'assigned_region': f"Unmapped: {country}",
        'routing_method': 'fallback_unmapped'
    }

def route_all(df, config_path):
    territory_config = load_territory(config_path)
    results = []
    for _, row in df.iterrows():
        result = route_lead(row.to_dict(), territory_config)
        results.append(result)
    return results

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    from src.ingest import load_leads
    config_path = os.getenv("TERRITORY_CONFIG_PATH", "config/territory.json")
    csv_path = os.getenv("LEADS_CSV_PATH", "data/leads.csv")
    df = load_leads(csv_path)
    results = route_all(df, config_path)
    for i, r in enumerate(results):
        company = df.iloc[i]['company_name']
        city = df.iloc[i]['city']
        country = df.iloc[i]['country']
        print(f"{company} ({city}, {country}) -> {r['assigned_rep']} [{r['routing_method']}]")
