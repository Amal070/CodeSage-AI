from typing import List, Dict, Any
from models.record import DataRecord
from services.api_client import ExternalApiClient

class DataProcessor:
    """Core processor for validating and transforming batch records."""
    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size
        self.api_client = ExternalApiClient()

    def process_batch(self, raw_items: List[Dict[str, Any]]) -> List[DataRecord]:
        """Transforms raw item dictionaries into validated DataRecord objects."""
        records = []
        for item in raw_items[:self.batch_size]:
            record = DataRecord(
                id=item['id'],
                value=float(item['value']),
                category=item.get('category', 'general'),
                status='processed',
            )
            records.append(record)
        return records

    def sync_to_cloud(self, records: List[DataRecord]) -> bool:
        """Sends processed records to external cloud API."""
        payload = [r.model_dump() for r in records]
        return self.api_client.post_records(payload)
