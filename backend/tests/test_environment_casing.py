"""ENVIRONMENT must behave the same regardless of casing/whitespace."""

import urllib.parse

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.services.kinescope_service import KinescopeService
from app.services.prodamus_service import ProdamusService


def test_settings_normalize_environment():
    s = Settings(_env_file=None, ENVIRONMENT=" Development ")
    assert s.ENVIRONMENT == "development"


def test_payment_link_has_no_demo_mode_for_capitalized_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "Production")
    monkeypatch.setattr(settings, "PRODAMUS_DEMO_MODE", False)
    url = ProdamusService.generate_payment_link(
        course_name="Course",
        price=5900,
        tariff="self",
        order_id="course|11111111-1111-1111-1111-111111111111|self|deadbeef",
    )
    params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
    assert "demo_mode" not in params


@pytest.mark.parametrize("env", ["Production", "STAGING"])
def test_kinescope_treats_capitalized_deployed_env_as_deployed(monkeypatch, env):
    monkeypatch.setattr(settings, "ENVIRONMENT", env)
    assert KinescopeService()._production is True


@pytest.mark.parametrize("env", ["prod", "Production-1", "preview", "dev"])
def test_unknown_environment_fails_at_startup(env):
    with pytest.raises(ValidationError, match="is not supported"):
        Settings(_env_file=None, ENVIRONMENT=env)


@pytest.mark.parametrize("env", ["development", "test"])
def test_local_environment_names_still_start(env):
    assert Settings(_env_file=None, ENVIRONMENT=env).ENVIRONMENT == env


def test_missing_environment_defaults_to_development(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert Settings(_env_file=None).ENVIRONMENT == "development"


@pytest.mark.parametrize("env", ["development", "test", "staging"])
def test_demo_payments_allowed_in_named_non_production(monkeypatch, env):
    monkeypatch.setattr(settings, "ENVIRONMENT", env)
    monkeypatch.setattr(settings, "PRODAMUS_DEMO_MODE", False)
    assert ProdamusService.demo_payments_allowed() is True


@pytest.mark.parametrize("env", ["production", "preview", "prod"])
def test_demo_payments_refused_outside_named_non_production(monkeypatch, env):
    # Settings refuses unknown names at startup; the runtime check must not
    # treat one as non-production either.
    monkeypatch.setattr(settings, "ENVIRONMENT", env)
    monkeypatch.setattr(settings, "PRODAMUS_DEMO_MODE", False)
    assert ProdamusService.demo_payments_allowed() is False
