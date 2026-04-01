"""
Tests for the cross-reference consensus logic.
"""

from listingjet.services.property_scraper.cross_reference import cross_reference


def test_consensus_all_agree():
    """API + 2 scraped sources all agree → verified, confidence 1.0."""
    api_data = {"beds": 3, "baths": 2, "sqft": 1500}
    scraped = {
        "zillow": {"beds": 3, "baths": 2, "sqft": 1500},
        "redfin": {"beds": 3, "baths": 2, "sqft": 1500},
    }
    result = cross_reference(api_data, scraped)

    assert result["status"] == "verified"
    assert result["mismatches"] == []
    assert result["sources_checked"] == ["zillow", "redfin"]
    assert result["field_confidence"]["beds"] == 1.0
    assert result["field_confidence"]["baths"] == 1.0
    assert result["field_confidence"]["sqft"] == 1.0


def test_mismatch_detected():
    """API says 3 beds, both scraped sources say 4 → mismatches_found."""
    api_data = {"beds": 3, "baths": 2}
    scraped = {
        "zillow": {"beds": 4, "baths": 2},
        "redfin": {"beds": 4, "baths": 2},
    }
    result = cross_reference(api_data, scraped)

    assert result["status"] == "mismatches_found"
    assert "beds" in result["mismatches"]
    assert "baths" not in result["mismatches"]
    # baths all agree → confidence 1.0
    assert result["field_confidence"]["baths"] == 1.0
    # beds: 0 agree, 2 disagree → confidence 0.0
    assert result["field_confidence"]["beds"] == 0.0


def test_missing_fields_ignored():
    """Scraped source only has some fields → still verified for present fields."""
    api_data = {"beds": 3, "baths": 2, "sqft": 1800}
    scraped = {
        "zillow": {"beds": 3},           # only has beds
        "redfin": {"beds": 3, "baths": 2},  # has beds + baths, no sqft
    }
    result = cross_reference(api_data, scraped)

    assert result["status"] == "verified"
    assert result["mismatches"] == []
    # beds: both sources agree → 1.0
    assert result["field_confidence"]["beds"] == 1.0
    # baths: only redfin has it, agrees → 1.0
    assert result["field_confidence"]["baths"] == 1.0
    # sqft: no source has it → 0.5 (no data)
    assert result["field_confidence"]["sqft"] == 0.5


def test_no_scraped_data_returns_partial():
    """Empty scraped dict → partial status, all fields at 0.5 confidence."""
    api_data = {"beds": 3, "baths": 2, "sqft": 1200}
    result = cross_reference(api_data, {})

    assert result["status"] == "partial"
    assert result["sources_checked"] == []
    assert result["mismatches"] == []
    assert result["field_confidence"]["beds"] == 0.5
    assert result["field_confidence"]["baths"] == 0.5
    assert result["field_confidence"]["sqft"] == 0.5


def test_sqft_tolerance():
    """sqft within 5% counts as matching; lot_sqft uses 10% tolerance."""
    api_data = {"sqft": 2000, "lot_sqft": 5000}
    scraped = {
        # sqft: 2080 is within 5% of 2000 (diff = 4%) → agree
        # lot_sqft: 5450 is within 10% of 5000 (diff = 9%) → agree
        "zillow": {"sqft": 2080, "lot_sqft": 5450},
        "redfin": {"sqft": 2080, "lot_sqft": 5450},
    }
    result = cross_reference(api_data, scraped)

    assert result["status"] == "verified"
    assert result["mismatches"] == []
    assert result["field_confidence"]["sqft"] == 1.0
    assert result["field_confidence"]["lot_sqft"] == 1.0


def test_sqft_outside_tolerance():
    """sqft outside 5% tolerance counts as disagreement."""
    api_data = {"sqft": 2000}
    scraped = {
        # 2200 is 10% off → outside 5% tolerance → disagree
        "zillow": {"sqft": 2200},
    }
    result = cross_reference(api_data, scraped)

    assert result["status"] == "mismatches_found"
    assert "sqft" in result["mismatches"]
