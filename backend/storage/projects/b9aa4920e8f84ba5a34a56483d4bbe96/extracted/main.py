import sys
from config import load_config
from services.processor import DataProcessor
from utils.logger import setup_logger

logger = setup_logger('data_pipeline')

def main():
    """Main application entry point for data ingestion."""
    cfg = load_config()
    logger.info('Initializing data pipeline for %s in %s mode', cfg.app_name, cfg.environment)
    processor = DataProcessor(batch_size=cfg.batch_size)
    sample_data = [
        {'id': 101, 'value': 250.0, 'category': 'hardware'},
        {'id': 102, 'value': 890.5, 'category': 'software'},
    ]
    processed_records = processor.process_batch(sample_data)
    success = processor.sync_to_cloud(processed_records)
    logger.info('Sync completed with status: %s', success)
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
