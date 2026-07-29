"""Turkish domain validators — TCKN, VKN, TR IBAN, and Turkish Phone Number algorithms.

Contains algorithmic validation logic for Turkish business entities.
No external dependencies — pure Python stdlib.
"""

from __future__ import annotations

import re


def validate_tckn(value: object) -> bool:
    """Validate Turkish Republic Identification Number (TC Kimlik No).

    Algorithmic Rules:
    1. Must be exactly 11 numeric digits.
    2. First digit cannot be '0'.
    3. 10th digit = ((sum(d1, d3, d5, d7, d9) * 7) - sum(d2, d4, d6, d8)) % 10
    4. 11th digit = sum(d1..d10) % 10

    Args:
        value: Candidate TCKN value (string or int).

    Returns:
        bool: True if TCKN is algorithmically valid.
    """
    if value is None:
        return False

    val_str = str(value).strip()

    # Rule 1 & 2: 11 digits, first digit != 0
    if not (len(val_str) == 11 and val_str.isdigit() and val_str[0] != "0"):
        return False

    digits = [int(c) for c in val_str]

    # Rule 3: 10th digit checksum
    odd_sum = digits[0] + digits[2] + digits[4] + digits[6] + digits[8]
    even_sum = digits[1] + digits[3] + digits[5] + digits[7]
    digit_10 = ((odd_sum * 7) - even_sum) % 10

    if digits[9] != digit_10:
        return False

    # Rule 4: 11th digit checksum
    digit_11 = sum(digits[:10]) % 10
    return digits[10] == digit_11


def validate_vkn(value: object) -> bool:
    """Validate Turkish Tax Identification Number (Vergi Kimlik No).

    Algorithmic Rules:
    1. Must be exactly 10 numeric digits.
    2. Uses MOD 10 checksum algorithm with 2^n weighting.

    Args:
        value: Candidate VKN value (string or int).

    Returns:
        bool: True if VKN is algorithmically valid.
    """
    if value is None:
        return False

    val_str = str(value).strip()

    if not (len(val_str) == 10 and val_str.isdigit()):
        return False

    digits = [int(c) for c in val_str]
    total = 0

    for i in range(9):
        tmp = (digits[i] + (9 - i)) % 10
        if tmp != 0:
            c = (tmp * (2 ** (9 - i))) % 9
            if c == 0:
                c = 9
        else:
            c = 0
        total += c

    check_digit = (10 - (total % 10)) % 10
    return digits[9] == check_digit


def validate_tr_iban(value: object) -> bool:
    """Validate Turkish IBAN (International Bank Account Number).

    Rules:
    1. Must start with 'TR' (case-insensitive).
    2. Must be followed by exactly 24 numeric digits (Total 26 chars).
    3. MOD 97 checksum validation.

    Args:
        value: Candidate IBAN string.

    Returns:
        bool: True if TR IBAN is valid.
    """
    if value is None:
        return False

    val_str = str(value).replace(" ", "").upper()

    if not (len(val_str) == 26 and val_str.startswith("TR") and val_str[2:].isdigit()):
        return False

    # MOD 97 checksum: Move 'TR00' to end -> 'TR' = 2927
    rearranged = val_str[4:] + "2927" + val_str[2:4]
    return int(rearranged) % 97 == 1


def validate_phone_tr(value: object) -> bool:
    """Validate Turkish Mobile Phone Number.

    Formats accepted:
    - 05xx xxx xx xx (e.g., '05321234567')
    - 5xx xxx xx xx (e.g., '5321234567')
    - +905xx xxx xx xx (e.g., '+905321234567')

    Args:
        value: Candidate phone number value.

    Returns:
        bool: True if phone number is a valid Turkish mobile number.
    """
    if value is None:
        return False

    val_str = re.sub(r"[\s\-\(\)]", "", str(value))

    # Pattern for Turkish mobile numbers (starts with +905, 05, or 5 and has 10 mobile digits)
    pattern = r"^(?:\+90|0)?5\d{9}$"
    return bool(re.match(pattern, val_str))
