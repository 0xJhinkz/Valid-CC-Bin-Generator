import os
import time
from typing import Optional

import requests
from bin_generator import (
    BIN_TYPES,
    generate_cards,
    lookup_bin,
    validate_card_number,
    format_bin_details,
)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "Telegram bot token not found. Set TELEGRAM_BOT_TOKEN in your environment."
    )

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

HELP_TEXT = (
    "Valid CC Bin Generator Bot\n\n"
    "Commands:\n"
    "/start - Show this message\n"
    "/help - Show this message\n"
    "/generate <type> <count> [bin_prefix] - Generate valid cards\n"
    "/generate <type> <count> <bin_prefix> - Use a custom BIN prefix\n"
    "/lookup <bin> - Lookup BIN details\n"
    "/validate <card_number> - Validate a card number with Luhn\n"
    "/visa <count> [bin_prefix] - Generate Visa cards\n"
    "/mastercard <count> [bin_prefix] - Generate Mastercard cards\n"
    "/amex <count> [bin_prefix] - Generate Amex cards\n"
    "/discover <count> [bin_prefix] - Generate Discover cards\n"
    "Example: /generate visa 3 453201"
)


def send_message(chat_id: int, text: str) -> None:
    requests.post(
        f"{BASE_URL}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    )


def get_updates(offset: Optional[int] = None) -> list[dict]:
    params = {"timeout": 30, "limit": 10}
    if offset is not None:
        params["offset"] = offset
    response = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=35)
    response.raise_for_status()
    result = response.json()
    return result.get("result", [])


def format_card_response(card_numbers: list[str]) -> str:
    return "\n".join(card_numbers)


def build_generate_response(args: str, default_type: Optional[str] = None) -> str:
    tokens = args.split()
    if len(tokens) < 1:
        return "Usage: /generate <type> <count> [bin_prefix]"

    if default_type and len(tokens) == 1:
        tokens.insert(0, default_type)

    if len(tokens) < 2:
        return "Usage: /generate <type> <count> [bin_prefix]"

    card_type_key = tokens[0].lower()
    if card_type_key not in BIN_TYPES:
        return "Bin type must be visa, mastercard, amex, or discover."

    try:
        count = int(tokens[1])
    except ValueError:
        return "Count must be a number."

    if count < 1 or count > 10:
        return "Count must be between 1 and 10."

    bin_prefix = tokens[2] if len(tokens) >= 3 else None
    card_type = BIN_TYPES[card_type_key]
    try:
        cards = generate_cards(card_type, count, prefix=bin_prefix)
    except ValueError as exc:
        return str(exc)

    return format_card_response(cards)


def build_lookup_response(args: str) -> str:
    bin_value = args.split()[0] if args else ""
    if not bin_value or not bin_value.isdigit():
        return "Usage: /lookup <bin>"

    details = lookup_bin(bin_value[:6])
    if details is None:
        return "BIN lookup failed or invalid BIN."
    return format_bin_details(details)


def build_validate_response(args: str) -> str:
    card_number = ''.join(args.split())
    if not card_number.isdigit():
        return "Usage: /validate <card_number>"

    if validate_card_number(card_number):
        return f"{card_number} is valid."
    return f"{card_number} is invalid."


def build_response(command: str, args: Optional[str]) -> str:
    command = command.lower()
    if command in ("start", "help"):
        return HELP_TEXT

    if command == "generate":
        return build_generate_response(args or "")

    if command in BIN_TYPES:
        return build_generate_response(args or "", default_type=command)

    if command == "lookup":
        return build_lookup_response(args or "")

    if command == "validate":
        return build_validate_response(args or "")

    return "Unknown command. Send /help for usage."


def handle_update(update: dict) -> None:
    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    if not text or not text.startswith("/"):
        return

    parts = text.split(maxsplit=1)
    command = parts[0][1:]
    args = parts[1] if len(parts) > 1 else ""
    response = build_response(command, args)
    send_message(chat_id, response)


def main() -> None:
    last_update_id = None
    while True:
        try:
            updates = get_updates(last_update_id + 1 if last_update_id is not None else None)
            for update in updates:
                last_update_id = update["update_id"]
                handle_update(update)
        except requests.RequestException:
            time.sleep(5)
        except Exception:
            time.sleep(5)


if __name__ == "__main__":
    main()
