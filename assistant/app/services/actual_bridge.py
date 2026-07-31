"""HTTP client for the Node bridge that talks to Actual Budget.

Actual Budget has no direct REST transaction API; the official
``@actual-app/api`` Node library is required. The bridge service exposes a
thin internal REST surface that this client consumes.

All methods degrade gracefully: on any error they raise ``BridgeError`` so
callers can queue the transaction for a later sync retry instead of losing it.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)


class BridgeError(Exception):
    """Raised when the Actual bridge is unreachable or returns an error."""


class ActualBridgeClient:
    def __init__(self, base_url: Optional[str], timeout: float = 20.0) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    def _request(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        if not self.enabled:
            raise BridgeError("bridge base_url not configured")
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "ignore")
            raise BridgeError(f"HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise BridgeError(str(exc)) from exc

    def health(self) -> dict:
        return self._request("GET", "/health")

    def list_accounts(self) -> list[dict]:
        return self._request("GET", "/accounts").get("accounts", [])

    def list_categories(self) -> list[dict]:
        return self._request("GET", "/categories").get("categories", [])

    def create_transaction(
        self,
        *,
        account_id: str,
        amount: float,
        payee_name: Optional[str],
        category_name: Optional[str],
        date: str,
        notes: Optional[str] = None,
        direction: str = "expense",
    ) -> dict:
        """Create a transaction in Actual Budget via the bridge.

        ``amount`` is a positive number; the bridge/Actual convention stores
        expenses as negative integer minor units. Direction disambiguates sign.
        """
        return self._request(
            "POST",
            "/transactions",
            {
                "accountId": account_id,
                "amount": amount,
                "payeeName": payee_name,
                "categoryName": category_name,
                "date": date,
                "notes": notes,
                "direction": direction,
            },
        )
