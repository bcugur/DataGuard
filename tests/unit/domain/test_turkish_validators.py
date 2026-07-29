"""Unit tests for Turkish domain validators (TCKN, VKN, IBAN, Phone)."""

from dataguard.domain.validators.turkish import (
    validate_phone_tr,
    validate_tckn,
    validate_tr_iban,
    validate_vkn,
)


def test_tckn_valid():
    # Valid algorithmic TCKN example: 10000000146
    assert validate_tckn("10000000146") is True
    assert validate_tckn(10000000146) is True


def test_tckn_invalid():
    assert validate_tckn("00000000146") is False  # Cannot start with 0
    assert validate_tckn("10000000145") is False  # Bad checksum
    assert validate_tckn("12345") is False        # Too short
    assert validate_tckn(None) is False


def test_vkn_valid():
    # Valid algorithmic VKN example: 1234567890
    assert validate_vkn("1234567890") is True


def test_vkn_invalid():
    assert validate_vkn("12345") is False
    assert validate_vkn("1111111111") is False
    assert validate_vkn(None) is False


def test_tr_iban_valid():
    # Valid TR IBAN format & MOD97 checksum: TR400006200000000000000001
    assert validate_tr_iban("TR400006200000000000000001") is True
    assert validate_tr_iban("tr400006200000000000000001") is True
    assert validate_tr_iban("TR40 0006 2000 0000 0000 0000 01") is True


def test_tr_iban_invalid():
    assert validate_tr_iban("US890006200000000000000001") is False  # Not TR
    assert validate_tr_iban("TR12345") is False                       # Too short
    assert validate_tr_iban(None) is False


def test_phone_tr_valid():
    assert validate_phone_tr("05321234567") is True
    assert validate_phone_tr("5321234567") is True
    assert validate_phone_tr("+90 532 123 45 67") is True
    assert validate_phone_tr("0 (532) 123 4567") is True


def test_phone_tr_invalid():
    assert validate_phone_tr("02121234567") is False  # Landline (not mobile)
    assert validate_phone_tr("123456") is False       # Too short
    assert validate_phone_tr(None) is False
