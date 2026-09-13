import requests
from typing import List, Dict, Any

class ExternalApiClient:
    """HTTP client interface for cloud synchronization."""
    def __init__(self, base_url: str = 'https://telemetry.pipeline.io/v1'):
        self.base_url = base_url

    def post_records(self, payload: List[Dict[str, Any]]) -> bool:
        try:
            resp = requests.post(f'{self.base_url}/records', json=payload, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False
