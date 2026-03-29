from types import SimpleNamespace

from launchlens.services.feature_tags import extract_features


def _vr(labels: list[str]):
    return SimpleNamespace(
        raw_labels={"labels": [{"name": name} for name in labels]}
    )


def test_extract_known_features():
    results = [_vr(["granite", "pool", "hardwood"])]
    tags = extract_features(results)
    assert "Granite Countertops" in tags
    assert "Swimming Pool" in tags
    assert "Hardwood Floors" in tags


def test_extract_no_matches():
    results = [_vr(["unknown_label", "something_else"])]
    assert extract_features(results) == []


def test_extract_deduplicates():
    results = [_vr(["pool"]), _vr(["swimming pool"])]
    tags = extract_features(results)
    assert tags.count("Swimming Pool") == 1


def test_extract_empty_raw_labels():
    vr = SimpleNamespace(raw_labels=None)
    assert extract_features([vr]) == []
