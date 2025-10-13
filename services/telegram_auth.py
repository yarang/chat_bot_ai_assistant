"""
Telegram Login authentication helpers.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field


class TelegramAuthPayload(BaseModel):
    """
    Pydantic model representing Telegram login widget payload.
    Extra fields are allowed to preserve future Telegram additions.
    """

    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = Field(default=None, alias="photo_url")
    auth_date: int
    hash: str

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    def to_data_check_string(self) -> str:
        """
        Build the data_check_string described in the Telegram login docs.
        """
        payload = self.model_dump(exclude_none=True, by_alias=True)
        payload.pop("hash", None)
        # Telegram requires keys sorted lexicographically and joined with newline.
        parts = [f"{key}={payload[key]}" for key in sorted(payload.keys())]
        return "\n".join(parts)

    def to_user_payload(self) -> Dict[str, Any]:
        """
        Return user-facing payload without the hash field.
        """
        return self.model_dump(exclude={"hash"}, exclude_none=True, by_alias=True)


def verify_telegram_auth(
    payload: TelegramAuthPayload,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> bool:
    """
    Verify Telegram login payload integrity and freshness.

    Args:
        payload: Parsed TelegramAuthPayload from the login widget.
        bot_token: Bot token used to derive the verification secret.
        max_age_seconds: Optional payload age limit. Defaults to 24h.

    Returns:
        True if the payload is valid; otherwise False.
    """
    if not bot_token:
        # Without a bot token we cannot derive the HMAC secret.
        return False

    expected_hash = _calculate_hash(payload, bot_token)
    if not hmac.compare_digest(expected_hash, payload.hash):
        return False

    if max_age_seconds and not _is_payload_fresh(payload.auth_date, max_age_seconds):
        return False

    return True


def _calculate_hash(payload: TelegramAuthPayload, bot_token: str) -> str:
    """
    Calculate expected hash from payload and bot token.
    """
    data_check_string = payload.to_data_check_string()
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    return hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()


def _is_payload_fresh(auth_date: int, max_age_seconds: int) -> bool:
    """
    Ensure the auth payload was generated within the allowed time window.
    """
    try:
        auth_ts = int(auth_date)
    except (TypeError, ValueError):
        return False

    current_ts = int(time.time())
    return (current_ts - auth_ts) <= max_age_seconds
