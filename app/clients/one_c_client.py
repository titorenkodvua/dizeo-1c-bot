import json
import logging
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

import httpx

logger = logging.getLogger(__name__)


class OneCClientError(Exception):
    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind


class OneCClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        timeout: float,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = (username, password)
        self._timeout = timeout

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            auth=self._auth,
            timeout=self._timeout,
            follow_redirects=True,
        )

    @staticmethod
    def _build_create_query(comment: str, sum_value: Decimal) -> str:
        # 1C на этой стороне ожидает %20 для пробела, а не '+'.
        encoded_comment = quote(comment, safe="")
        encoded_sum = quote(str(sum_value), safe="")
        return f"comment={encoded_comment}&sum={encoded_sum}"

    @staticmethod
    def _append_query(url: str, query: str) -> str:
        parsed = urlsplit(url)
        return urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment)
        )

    async def get_cash_expense_orders(self, limit: int) -> dict[str, Any]:
        safe_log = f"GET cash-expense-orders limit={limit}"
        logger.info("1C request: %s", safe_log)
        try:
            async with self._client() as client:
                r = await client.get(
                    "/cash-expense-orders",
                    params={"limit": limit},
                )
        except httpx.TimeoutException as e:
            logger.warning("1C timeout: %s", safe_log)
            raise OneCClientError("timeout") from e
        except httpx.RequestError as e:
            logger.warning("1C request error: %s", e)
            raise OneCClientError("request") from e

        if r.status_code >= 400:
            logger.warning(
                "1C HTTP error: status=%s path=cash-expense-orders",
                r.status_code,
            )
            raise OneCClientError("http")

        try:
            return r.json()
        except ValueError as e:
            ct = r.headers.get("content-type", "")
            preview = (r.text or "")[:200].replace("\n", " ")
            logger.warning(
                "1C response is not JSON: status=%s content-type=%r preview=%r",
                r.status_code,
                ct,
                preview,
            )
            raise OneCClientError("parse") from e

    async def create_cash_expense_order(
        self,
        comment: str,
        sum_value: Decimal,
    ) -> str:
        query = self._build_create_query(comment, sum_value)
        create_path = f"/cash-expense-orders?{query}"
        safe_log = "POST cash-expense-orders comment_len=%s sum=%s"
        logger.info(
            safe_log,
            len(comment),
            str(sum_value),
        )
        try:
            async with self._client() as client:
                r = await client.post(
                    create_path,
                    follow_redirects=False,
                )
                if 300 <= r.status_code < 400:
                    location = r.headers.get("location", "")
                    if not location:
                        logger.warning(
                            "1C create got redirect without location: status=%s",
                            r.status_code,
                        )
                        raise OneCClientError("redirect")
                    redirected_url = urljoin(str(r.request.url), location)
                    redirected_url = self._append_query(redirected_url, query)
                    logger.info(
                        "1C create redirect: status=%s -> POST %s",
                        r.status_code,
                        redirected_url,
                    )
                    r = await client.post(
                        redirected_url,
                        follow_redirects=False,
                    )
        except httpx.TimeoutException as e:
            logger.warning("1C timeout on create")
            raise OneCClientError("timeout") from e
        except httpx.RequestError as e:
            logger.warning("1C request error on create: %s", e)
            raise OneCClientError("request") from e

        if r.status_code >= 400:
            logger.warning("1C HTTP error on create: status=%s", r.status_code)
            raise OneCClientError("http")

        body = r.text
        ct = r.headers.get("content-type", "")
        if "application/json" in ct:
            try:
                body = json.dumps(r.json(), ensure_ascii=False, indent=2)
            except ValueError:
                body = r.text
        logger.info("1C RKO created successfully")
        return body
