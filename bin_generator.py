import datetime
from typing import Optional

import requests
import rstr

BIN_TYPES = {
    "mastercard": "Mastercard",
    "visa": "Visa",
    "amex": "Amex",
    "discover": "Discover",
}


def generate_bin(bin_type: str) -> str:
    if bin_type == "Mastercard":
        return rstr.xeger(r"5\d{5}")
    if bin_type == "Visa":
        return rstr.xeger(r"4\d{5}")
    if bin_type == "Amex":
        return rstr.xeger(r"3\d{5}")
    if bin_type == "Discover":
        return rstr.xeger(r"6\d{5}")
    raise ValueError(f"Unsupported bin type: {bin_type}")


def card_length_for_type(bin_type: str) -> int:
    return 15 if bin_type == "Amex" else 16


def luhn_checksum(number: str) -> int:
    digits = [int(d) for d in number[::-1]]
    total = 0
    for i, digit in enumerate(digits):
        if i % 2 == 0:
            total += digit
        else:
            doubled = digit * 2
            total += doubled - 9 if doubled > 9 else doubled
    return total % 10


def make_luhn_number(prefix: str, length: int = 16) -> str:
    if not prefix.isdigit():
        raise ValueError("Prefix must contain only digits.")
    if len(prefix) >= length:
        raise ValueError("Prefix must be shorter than the final card length.")

    number = prefix
    while len(number) < length - 1:
        number += str(rstr.digit())

    check_value = luhn_checksum(number + "0")
    check_digit = 0 if check_value == 0 else 10 - check_value
    return number + str(check_digit)


def generate_cards(bin_type: str, count: int, prefix: Optional[str] = None) -> list[str]:
    if prefix and prefix.isdigit():
        base_prefix = prefix
    else:
        base_prefix = generate_bin(bin_type)

    length = card_length_for_type(bin_type)
    return [make_luhn_number(base_prefix, length) for _ in range(count)]


def validate_card_number(number: str) -> bool:
    sanitized = ''.join(ch for ch in number if ch.isdigit())
    if len(sanitized) < 12:
        return False
    return luhn_checksum(sanitized[:-1] + '0') == int(sanitized[-1])


def generate_bins(bin_type: str, count: int) -> list[str]:
    return [generate_bin(bin_type) for _ in range(count)]


def lookup_bin(bin_value: str) -> Optional[dict]:
    url = f"https://binlist.io/lookup/{bin_value}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return None

    if data.get("success") is False:
        return None

    return {
        "bin": bin_value,
        "scheme": data.get("scheme", "N/A"),
        "type": data.get("type", "N/A"),
        "category": data.get("category", "N/A"),
        "country": data.get("country", {}).get("name", "N/A"),
        "bank": data.get("bank", {}).get("name", "N/A"),
    }


def format_bin_details(data: dict) -> str:
    return (
        f"Bin      : {data['bin']}\n"
        f"Scheme   : {data['scheme']}\n"
        f"Type     : {data['type']}\n"
        f"Category : {data['category']}\n"
        f"Country  : {data['country']}\n"
        f"Bank     : {data['bank']}"
    )


def save_bins_to_file(text: str, path: str | None = None) -> str:
    timestamp = datetime.datetime.now().strftime("%d-%m-%y %I-%M-%S-%p")
    path = path or f"Results/[Valid Bins] {timestamp}.txt"
    with open(path, "a", encoding="utf-8") as file:
        file.write(text)
    return path
