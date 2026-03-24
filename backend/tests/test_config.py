# backend/tests/test_config.py
import os
import pytest
from unittest.mock import patch


def test_settings_load_from_env():
    env = {
        "ANTHROPIC_API_KEY": "test-key",
        "SERP_API_KEY": "serp-key",
        "SCOUT_MODEL": "claude-haiku-4-5",
        "JOB_MATCH_THRESHOLD": "0.7",
        "DATABASE_URL": "sqlite:///./test.db",
        "UPLOAD_DIR": "uploads",
    }
    with patch.dict(os.environ, env, clear=True):
        from importlib import reload
        import backend.config as cfg
        reload(cfg)
        s = cfg.Settings()
        assert s.ANTHROPIC_API_KEY == "test-key"
        assert s.JOB_MATCH_THRESHOLD == 0.7
        assert s.SCOUT_MODEL == "claude-haiku-4-5"


def test_default_values():
    env = {
        "ANTHROPIC_API_KEY": "key",
        "SERP_API_KEY": "serp",
        "DATABASE_URL": "sqlite:///./test.db",
        "UPLOAD_DIR": "uploads",
    }
    with patch.dict(os.environ, env, clear=True):
        from importlib import reload
        import backend.config as cfg
        reload(cfg)
        s = cfg.Settings()
        assert s.JOB_MATCH_THRESHOLD == 0.6
        assert s.SCOUT_MODEL == "anthropic/claude-haiku-4-5"
        assert s.WEBHOOK_BYPASS_THRESHOLD is False
