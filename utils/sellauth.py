"""Minimal async client for the SellAuth API.

Docs: https://docs.sellauth.com
Add new endpoints here as small methods, then call them from any cog
through `self.bot.sellauth`.
"""
from __future__ import annotations

from typing import Any

import aiohttp


class SellAuthError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class SellAuthClient:
    BASE_URL = "https://api.sellauth.com/v1"

    def __init__(self, api_key: str, shop_id: str):
        self.api_key = api_key
        self.shop_id = shop_id
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=20),
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        session = await self._get_session()
        async with session.request(method, f"{self.BASE_URL}{path}", **kwargs) as resp:
            try:
                data = await resp.json(content_type=None)
            except Exception:
                data = await resp.text()
            if resp.status >= 400:
                msg = data.get("message") if isinstance(data, dict) else str(data)
                raise SellAuthError(resp.status, msg or "Unknown API error")
            return data

    def _shop(self, path: str = "") -> str:
        return f"/shops/{self.shop_id}{path}"

    # ---------- Shop ----------
    async def get_shop(self) -> dict:
        return await self.request("GET", self._shop())

    async def get_stats(self) -> dict:
        return await self.request("GET", self._shop("/stats"))

    # ---------- Products ----------
    async def list_products(self, page: int = 1) -> Any:
        return await self.request("GET", self._shop("/products"), params={"page": page})

    async def get_product(self, product_id: int) -> dict:
        return await self.request("GET", self._shop(f"/products/{product_id}"))

    # ---------- Invoices ----------
    async def list_invoices(self, page: int = 1, **filters: Any) -> Any:
        params = {"page": page, **{k: v for k, v in filters.items() if v is not None}}
        return await self.request("GET", self._shop("/invoices"), params=params)

    async def get_invoice(self, invoice_id: int) -> dict:
        return await self.request("GET", self._shop(f"/invoices/{invoice_id}"))

    # ---------- Customers ----------
    async def list_customers(self, page: int = 1) -> Any:
        return await self.request("GET", self._shop("/customers"), params={"page": page})

    # ---------- Coupons ----------
    async def list_coupons(self, page: int = 1) -> Any:
        return await self.request("GET", self._shop("/coupons"), params={"page": page})


def unwrap(data: Any) -> Any:
    """Paginated responses usually look like {"data": [...]}. Return the inner part."""
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data


def pick(d: dict, *keys: str, default: Any = "N/A") -> Any:
    """Return the first non-empty value among keys (API field names can vary)."""
    for k in keys:
        if d.get(k) not in (None, ""):
            return d[k]
    return default
