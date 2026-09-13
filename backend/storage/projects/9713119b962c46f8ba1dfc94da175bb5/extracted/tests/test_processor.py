from services.processor import DataProcessor

def test_process_batch():
    proc = DataProcessor(batch_size=5)
    results = proc.process_batch([{'id': 1, 'value': 99.0}])
    assert len(results) == 1
    assert results[0].status == 'processed'
