"""ENVIRONMENT must behave the same regardless of casing/whitespace."""

import urllib.parse

import pytest

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
