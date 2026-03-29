from listingjet.services.pii_filter import sanitize_for_prompt


def test_strips_pii_fields():
    data = {
        "address": "123 Main St",
        "agent_name": "John Doe",
        "agent_email": "john@example.com",
        "price": 500000,
    }
    result = sanitize_for_prompt(data)
    assert "address" in result
    assert "price" in result
    assert "agent_name" not in result
    assert "agent_email" not in result


def test_strips_nested_pii():
    data = {
        "listing": {
            "address": "456 Elm St",
            "contact_phone": "555-1234",
        },
        "owner_name": "Jane",
    }
    result = sanitize_for_prompt(data)
    assert "owner_name" not in result
    assert "contact_phone" not in result["listing"]
    assert result["listing"]["address"] == "456 Elm St"


def test_non_dict_passthrough():
    assert sanitize_for_prompt("just a string") == "just a string"


def test_empty_dict():
    assert sanitize_for_prompt({}) == {}
