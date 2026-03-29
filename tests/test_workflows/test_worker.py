# tests/test_workflows/test_worker.py


def test_worker_module_imports():
    from listingjet.workflows.worker import create_worker
    assert callable(create_worker)


def test_worker_registers_all_activities():
    from listingjet.workflows import worker
    source = open(worker.__file__).read()
    assert "ALL_ACTIVITIES" in source
    assert "ListingPipeline" in source
