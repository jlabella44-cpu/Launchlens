"""Tests for scripts/gen_env_example.py."""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "gen_env_example.py"
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"


def _load_module():
    spec = importlib.util.spec_from_file_location("gen_env_example", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gen_env_example():
    return _load_module()


def test_emits_a_line_for_every_settings_field(gen_env_example):
    from listingjet.config import Settings

    lines = gen_env_example.generate_lines()
    body = "\n".join(lines)

    for name in Settings.model_fields:
        assert f"\n{name.upper()}=" in body or body.startswith(f"{name.upper()}="), (
            f"expected a line for {name.upper()} in generated .env.example content"
        )


def test_secret_fields_are_blanked_with_comment(gen_env_example):
    lines = gen_env_example.generate_lines()
    body = "\n".join(lines)

    assert "JWT_SECRET=  # secret" in body
    assert "DATABASE_URL=  # secret" in body
    assert "STRIPE_SECRET_KEY=  # secret" in body


def test_boolean_defaults_render_lowercase(gen_env_example):
    assert gen_env_example.format_default(True) == "true"
    assert gen_env_example.format_default(False) == "false"


def test_none_default_renders_empty(gen_env_example):
    assert gen_env_example.format_default(None) == ""


def test_list_default_renders_comma_joined(gen_env_example):
    assert gen_env_example.format_default(["a", "b", "c"]) == "a,b,c"


def test_check_passes_against_committed_env_example(gen_env_example, capsys):
    assert ENV_EXAMPLE_PATH.exists(), ".env.example must be committed"
    committed = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    generated = gen_env_example.generate_content()
    assert committed == generated, (
        ".env.example is stale — run `python scripts/gen_env_example.py` to regenerate"
    )


def test_check_mode_exits_nonzero_when_file_is_stale(gen_env_example, tmp_path, monkeypatch):
    stale_path = tmp_path / ".env.example"
    stale_path.write_text("STALE=true\n", encoding="utf-8")
    monkeypatch.setattr(gen_env_example, "ENV_EXAMPLE_PATH", stale_path)

    monkeypatch.setattr(sys, "argv", ["gen_env_example.py", "--check"])
    exit_code = gen_env_example.main()

    assert exit_code == 1


def test_check_mode_exits_zero_when_file_matches(gen_env_example, tmp_path, monkeypatch):
    fresh_path = tmp_path / ".env.example"
    fresh_path.write_text(gen_env_example.generate_content(), encoding="utf-8")
    monkeypatch.setattr(gen_env_example, "ENV_EXAMPLE_PATH", fresh_path)

    monkeypatch.setattr(sys, "argv", ["gen_env_example.py", "--check"])
    exit_code = gen_env_example.main()

    assert exit_code == 0
