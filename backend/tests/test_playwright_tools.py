import pytest
from unittest.mock import patch, MagicMock


def make_mock_input(name, input_type="text", label="", placeholder=""):
    m = MagicMock()
    m.get_attribute.side_effect = lambda attr: {
        "name": name, "type": input_type, "id": name,
        "placeholder": placeholder,
    }.get(attr, "")
    return m


def test_fetch_application_form_returns_field_list():
    mock_page = MagicMock()
    mock_inputs = [
        make_mock_input("first_name"), make_mock_input("email", "email"),
        make_mock_input("resume", "file"),
    ]
    mock_page.query_selector_all.return_value = mock_inputs
    mock_page.title.return_value = "Apply at Acme"

    with patch("backend.tools.playwright_tools.sync_playwright") as mock_pw:
        mock_pw.return_value.__enter__.return_value.chromium.launch.return_value \
            .__enter__.return_value.new_page.return_value = mock_page
        from backend.tools.playwright_tools import fetch_application_form
        result = fetch_application_form("https://acme.com/apply")

    assert isinstance(result["fields"], list)
    assert any(f["name"] == "first_name" for f in result["fields"])
    # File inputs should be excluded from auto-fill
    assert not any(f["type"] == "file" for f in result["fields"])


def test_fetch_application_form_returns_manual_required_on_error():
    with patch("backend.tools.playwright_tools.sync_playwright") as mock_pw:
        mock_pw.return_value.__enter__.return_value.chromium.launch.side_effect = Exception("browser error")
        from backend.tools.playwright_tools import fetch_application_form
        result = fetch_application_form("https://acme.com/apply")
    assert result["status"] == "manual_required"
    assert result["url"] == "https://acme.com/apply"
