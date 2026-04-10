# tests/test_workflows/test_worker.py


def test_worker_module_imports():
    from listingjet.workflows.worker import create_worker
    assert callable(create_worker)


def test_worker_registers_all_activities():
    from pathlib import Path

    from listingjet.workflows import worker
    source = Path(worker.__file__).read_text()
    assert "ALL_ACTIVITIES" in source
    assert "ListingPipeline" in source
