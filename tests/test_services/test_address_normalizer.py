from listingjet.services.address_normalizer import (
    normalize_address,
    address_hash,
    generate_alternates,
)


def test_normalize_expands_st_to_street():
    assert normalize_address("123 Main St") == "123 main street"


def test_normalize_expands_ct_to_court():
    assert normalize_address("456 Oak Ct") == "456 oak court"


def test_normalize_expands_ter_to_terrace():
    assert normalize_address("789 Pine Ter") == "789 pine terrace"


def test_normalize_strips_unit_number():
    # "100 Main St Apt 4B" → strips "Apt 4B"
    assert normalize_address("100 Main St Apt 4B") == "100 main street"


def test_normalize_strips_hash_unit():
    # "100 Main St #4" → strips "#4"
    assert normalize_address("100 Main St #4") == "100 main street"


def test_normalize_handles_already_expanded():
    assert normalize_address("123 Main Street") == "123 main street"


def test_normalize_handles_drive():
    assert normalize_address("55 Sunset Dr") == "55 sunset drive"


def test_address_hash_deterministic():
    h1 = address_hash("123 Oak St")
    h2 = address_hash("123 Oak St")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest length


def test_address_hash_normalizes_before_hashing():
    # "123 Oak St" and "123 oak street" should produce the same hash
    assert address_hash("123 Oak St") == address_hash("123 oak street")


def test_generate_alternates_from_street():
    # "123 Oak Street" should generate the abbreviated form "123 Oak St"
    alternates = generate_alternates("123 Oak Street")
    assert any("st" in alt.lower() and "street" not in alt.lower() for alt in alternates)


def test_generate_alternates_from_ct():
    # "456 Elm Ct" normalizes to "456 elm court", so alternate is abbreviated "ct"
    alternates = generate_alternates("456 Elm Ct")
    assert any("ct" in alt.split() for alt in alternates)


def test_generate_alternates_no_suffix_returns_empty():
    # An address with no recognized suffix returns no alternates
    alternates = generate_alternates("123 Oak")
    assert alternates == []
