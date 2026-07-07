"""Unit tests for certificate number generation and its uniqueness-retry loop.

DB-free: exercises CertificateService.generate_certificate_number and the
injectable _generate_unique_certificate_number helper directly, without
touching the database. See test_certificate_renderer.py's docstring — the
session-scoped `prepare_database` fixture in conftest.py is still autouse
regardless, so running this file requires the same DATABASE_URL/ENVIRONMENT
overrides as any other test in this suite.
"""

import re

import pytest

from app.services.certificate_service import (
    _CERTIFICATE_NUMBER_ALPHABET,
    CertificateService,
)

_NUMBER_PATTERN = re.compile(r"^LN-\d{4}-[2-9A-HJ-NP-Z]{6}$")


def test_generate_certificate_number_matches_format():
    for _ in range(200):
        number = CertificateService.generate_certificate_number()
        assert _NUMBER_PATTERN.fullmatch(number), number


def test_certificate_number_alphabet_excludes_ambiguous_characters():
    # 0/O and 1/I/L are excluded to avoid ambiguity on a printed diploma.
    for ambiguous in "0O1IL":
        assert ambiguous not in _CERTIFICATE_NUMBER_ALPHABET
    assert len(_CERTIFICATE_NUMBER_ALPHABET) == 31
    assert len(set(_CERTIFICATE_NUMBER_ALPHABET)) == 31


@pytest.mark.asyncio
async def test_generate_unique_certificate_number_retries_on_collision(monkeypatch: pytest.MonkeyPatch):
    candidates = iter(["LN-2026-AAAAAA", "LN-2026-BBBBBB"])
    monkeypatch.setattr(
        CertificateService,
        "generate_certificate_number",
        staticmethod(lambda: next(candidates)),
    )

    taken = {"LN-2026-AAAAAA"}

    async def is_taken(candidate: str) -> bool:
        return candidate in taken

    number = await CertificateService._generate_unique_certificate_number(is_taken)

    assert number == "LN-2026-BBBBBB"


@pytest.mark.asyncio
async def test_generate_unique_certificate_number_gives_up_after_max_attempts(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        CertificateService,
        "generate_certificate_number",
        staticmethod(lambda: "LN-2026-AAAAAA"),
    )

    async def always_taken(_candidate: str) -> bool:
        return True

    number = await CertificateService._generate_unique_certificate_number(always_taken)

    assert number is None
