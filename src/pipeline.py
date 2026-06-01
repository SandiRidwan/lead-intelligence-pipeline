import os
import sys
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, '.')

log_file = f"logs/pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from src.ingest import load_leads
from src.enrich import enrich_all
from src.geoRoute import route_all
from src.score import score_all
from src.notify import notify_high_priority
from src.output import build_output_rows, save_to_csv, save_to_google_sheet

def run_pipeline():
    start = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info("LEAD INTELLIGENCE PIPELINE STARTED")
    logger.info(f"Run time: {start.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("=" * 60)

    csv_path = os.getenv("LEADS_CSV_PATH", "data/leads.csv")
    config_path = os.getenv("TERRITORY_CONFIG_PATH", "config/territory.json")

    try:
        logger.info("[1/5] INGESTION")
        df = load_leads(csv_path)
        logger.info(f"Clean leads: {len(df)}")

        logger.info("[2/5] ENRICHMENT")
        enriched = enrich_all(df)
        logger.info(f"Enriched: {len(enriched)} leads")

        logger.info("[3/5] GEO-ROUTING")
        routed = route_all(df, config_path)
        logger.info(f"Routed: {len(routed)} leads")

        logger.info("[4/5] SCORING")
        scored = score_all(enriched)
        high = sum(1 for s in scored if s['is_high_priority'])
        logger.info(f"Scored: {len(scored)} leads | HIGH PRIORITY: {high}")

        logger.info("[5/5] OUTPUT + NOTIFICATIONS")
        rows = build_output_rows(df, enriched, scored, routed)
        csv_out = save_to_csv(rows)
        gsheet = save_to_google_sheet(rows)
        sent = notify_high_priority(df, enriched, scored, routed)

        end = datetime.now(timezone.utc)
        duration = (end - start).seconds

        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETE")
        logger.info(f"Total leads processed : {len(df)}")
        logger.info(f"HIGH PRIORITY         : {high}")
        logger.info(f"NORMAL                : {len(df) - high}")
        logger.info(f"Slack alerts sent     : {sent}")
        logger.info(f"CSV output            : {csv_out}")
        logger.info(f"Google Sheet          : {'Updated' if gsheet else 'Skipped (no credentials)'}")
        logger.info(f"Duration              : {duration}s")
        logger.info(f"Log file              : {log_file}")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"PIPELINE FAILED: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = run_pipeline()
    sys.exit(0 if success else 1)
