"""Async client + helpers for the SellAuth API.

Docs: https://docs.sellauth.com/api-documentation
Anything marked VERIFY could not be confirmed from the public docs.
If a command errors, the API's own message is shown in Discord.
"""
from __future__ import annotations

from typing import Any

import aiohttp


class SellAuthError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _q(params: dict | None) -> list[tuple[str, str]] | None:
    """Turn a dict into query params (lists become key[]=a&key[]=b)."""
    if not params:
        return None
    out: list[tuple[str, str]] = []
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, (list, tuple, set)):
            out += [(f"{k}[]", str(i)) for i in v]
        elif isinstance(v, bool):
            out.append((k, "1" if v else "0"))
        else:
            out.append((k, str(v)))
    return out or None


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

    async def request(self, method: str, path: str, *, params: dict | None = None, json: Any = None) -> Any:
        session = await self._get_session()
        async with session.request(method, f"{self.BASE_URL}{path}", params=_q(params), json=json) as resp:
            try:
                data = await resp.json(content_type=None)
            except Exception:
                data = await resp.text()
            if resp.status >= 400:
                msg = None
                if isinstance(data, dict):
                    msg = data.get("message")
                    if data.get("errors"):
                        msg = f"{msg} {data['errors']}"
                raise SellAuthError(resp.status, str(msg or data or "Unknown API error")[:500])
            return data

    async def _action(self, path: str) -> Any:
        """State-changing endpoints whose HTTP verb isn't documented (VERIFY): try POST, then PUT."""
        try:
            return await self.request("POST", path)
        except SellAuthError as e:
            if e.status in (404, 405):
                return await self.request("PUT", path)
            raise

    def _shop(self, path: str = "") -> str:
        return f"/shops/{self.shop_id}{path}"

    # ---------- Shop ----------
    async def get_shop(self) -> dict:
        return await self.request("GET", self._shop())

    async def get_stats(self) -> dict:
        return await self.request("GET", "/shops/%s/stats" % self.shop_id)

    # ---------- Analytics (VERIFY response keys) ----------
    async def analytics(self) -> Any:
        return await self.request("GET", self._shop("/analytics"))

    async def top_products(self) -> Any:
        return await self.request("GET", self._shop("/analytics/top-products"))

    async def top_customers(self) -> Any:
        return await self.request("GET", self._shop("/analytics/top-customers"))

    # ---------- Products ----------
    async def list_products(self, page: int = 1, per_page: int = 15) -> Any:
        return await self.request("GET", self._shop("/products"), params={"page": page, "perPage": per_page})

    async def all_products(self, max_pages: int = 10) -> list[dict]:
        items: list[dict] = []
        for page in range(1, max_pages + 1):
            data = await self.list_products(page, per_page=100)
            items += as_list(data)
            last = data.get("last_page") if isinstance(data, dict) else None
            if not last or page >= last:
                break
        return items

    async def get_product(self, product_id: str) -> dict:
        return await self.request("GET", self._shop(f"/products/{product_id}"))

    async def create_product(self, payload: dict) -> Any:  # VERIFY payload fields
        return await self.request("POST", self._shop("/products"), json=payload)

    async def update_product(self, product_id: str, payload: dict) -> Any:  # VERIFY path
        try:
            return await self.request("PUT", self._shop(f"/products/{product_id}/update"), json=payload)
        except SellAuthError as e:
            if e.status in (404, 405):
                return await self.request("PUT", self._shop(f"/products/{product_id}"), json=payload)
            raise

    async def delete_product(self, product_id: str) -> Any:
        return await self.request("DELETE", self._shop(f"/products/{product_id}"))

    async def clone_product(self, product_id: str) -> Any:  # VERIFY verb
        return await self._action(self._shop(f"/products/{product_id}/clone"))

    # ---------- Invoices (orders) ----------
    async def list_invoices(self, page: int = 1, per_page: int = 15, **filters: Any) -> Any:
        params = {"page": page, "perPage": per_page, "orderColumn": "id", "orderDirection": "desc", **filters}
        return await self.request("GET", self._shop("/invoices"), params=params)

    async def get_invoice(self, invoice_id: str) -> dict:
        return await self.request("GET", self._shop(f"/invoices/{invoice_id}"))

    async def refund_invoice(self, invoice_id: str) -> Any:  # VERIFY verb
        return await self._action(self._shop(f"/invoices/{invoice_id}/refund"))

    async def cancel_invoice(self, invoice_id: str) -> Any:  # VERIFY verb
        return await self._action(self._shop(f"/invoices/{invoice_id}/cancel"))

    async def process_invoice(self, invoice_id: str) -> Any:  # VERIFY verb (re-processes / re-delivers)
        return await self._action(self._shop(f"/invoices/{invoice_id}/process"))

    # ---------- Customers ----------
    async def list_customers(self, page: int = 1, per_page: int = 15, email: str | None = None) -> Any:
        return await self.request(
            "GET", self._shop("/customers"), params={"page": page, "perPage": per_page, "email": email}
        )

    # ---------- Coupons ----------
    async def list_coupons(self, page: int = 1, per_page: int = 15) -> Any:
        return await self.request("GET", self._shop("/coupons"), params={"page": page, "perPage": per_page})

    async def create_coupon(self, payload: dict) -> Any:
        return await self.request("POST", self._shop("/coupons"), json=payload)

    async def delete_coupon(self, coupon_id: str) -> Any:
        return await self.request("DELETE", self._shop(f"/coupons/{coupon_id}"))

    async def delete_used_coupons(self) -> Any:
        return await self.request("DELETE", self._shop("/coupons/used"))

    # ---------- Blacklist ----------
    async def list_blacklist(self, page: int = 1, per_page: int = 20) -> Any:
        return await self.request("GET", self._shop("/blacklist"), params={"page": page, "perPage": per_page})

    async def add_blacklist(self, payload: dict) -> Any:
        return await self.request("POST", self._shop("/blacklist"), json=payload)

    async def delete_blacklist(self, entry_id: str) -> Any:
        return await self.request("DELETE", self._shop(f"/blacklist/{entry_id}"))


# ---------- Helpers ----------
def unwrap(data: Any) -> Any:
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data


def as_list(data: Any) -> list:
    inner = unwrap(data)
    return inner if isinstance(inner, list) else []


def pick(d: Any, *keys: str, default: Any = "N/A") -> Any:
    """First non-empty value among keys (API field names can vary)."""
    if not isinstance(d, dict):
        return default
    for k in keys:
        if d.get(k) not in (None, ""):
            return d[k]
    return default


def money(v: Any) -> str:
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return str(v)


def page_text(data: Any, page: int) -> str:
    if isinstance(data, dict) and data.get("last_page"):
        total = data.get("total")
        return f"Page {page}/{data['last_page']}" + (f" | {total} total" if total is not None else "")
    return f"Page {page}"


def scalars(d: dict, prefix: str = "", depth: int = 1) -> list[tuple[str, str]]:
    """Flatten simple values out of a dict for generic embeds."""
    out: list[tuple[str, str]] = []
    for k, v in d.items():
        name = f"{prefix}{k}".replace("_", " ").title()
        if isinstance(v, bool) or isinstance(v, (str, int, float)):
            low = k.lower()
            if isinstance(v, (int, float)) and not isinstance(v, bool) and any(
                w in low for w in ("usd", "revenue", "price", "spent", "saved")
            ):
                out.append((name, money(v)))
            else:
                out.append((name, str(v)[:200]))
        elif isinstance(v, dict) and depth > 0:
            out += scalars(v, prefix=f"{k} ", depth=depth - 1)
    return out


def _to_int(v: Any) -> int | None:
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return None
    return None if n < 0 else n  # negative = unlimited


def stock_rows(product: dict) -> list[tuple[str, int | None, Any]]:
    """[(label, stock or None if unlimited/unknown, variant_id)] (VERIFY stock field names)."""
    name = pick(product, "name", default="Product")
    keys = ("stock_count", "stock", "stock_amount")
    rows = []
    variants = product.get("variants") or []
    for v in variants:
        label = f"{name} - {pick(v, 'name', default='Default')}"
        rows.append((label, _to_int(pick(v, *keys, default=None)), pick(v, "id", default=None)))
    if not variants:
        rows.append((str(name), _to_int(pick(product, *keys, default=None)), None))
    return rows
