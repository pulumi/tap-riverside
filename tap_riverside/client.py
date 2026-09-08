"""REST client handling, including RiversideStream base class.

The Riverside Business API v3 (https://platform.riverside.fm/api/v3) is a REST
API: Bearer-token auth, list endpoints that return an ``items[]`` array with
cursor pagination (``page.next_cursor``, driven by the ``cursor`` / ``limit``
query params, ``limit`` max 500). The API is rate limited to 1 request per
second, so the base stream throttles all requests across streams. See
https://docs.riverside.fm for the full spec.
"""

from __future__ import annotations

import decimal
import time
import typing as t

from singer_sdk.authenticators import BearerTokenAuthenticator
from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.pagination import BaseAPIPaginator
from singer_sdk.streams import RESTStream

if t.TYPE_CHECKING:
    import requests
    from singer_sdk.helpers.types import Context

DEFAULT_API_URL = "https://platform.riverside.fm"
DEFAULT_PAGE_SIZE = 500  # API maximum

# Riverside enforces 1 request/second per account.
REQUEST_INTERVAL_SECONDS = 1.0


class RiversidePaginator(BaseAPIPaginator):
    """Cursor paginator for Riverside list endpoints.

    Riverside responses carry a ``page`` envelope; we feed ``page.next_cursor``
    back as the ``cursor`` query param until it comes back null.
    """

    def __init__(self) -> None:
        """Start with no cursor (first page)."""
        super().__init__(None)

    def get_next(self, response: requests.Response) -> str | None:
        """Return the next cursor, or ``None`` when the last page is reached.

        Args:
            response: The most recent API response.

        Returns:
            The ``page.next_cursor`` value, else ``None``.
        """
        page = response.json().get("page") or {}
        return page.get("next_cursor")


class RiversideStream(RESTStream):
    """Riverside stream base class."""

    # Riverside list endpoints wrap results in an ``items`` array.
    records_jsonpath = "$.items[*]"

    # Shared across all streams so the whole tap respects the account-level
    # 1 req/s budget.
    _last_request_at: t.ClassVar[float] = 0.0

    @property
    def url_base(self) -> str:
        """Return the API URL root, configurable via tap settings."""
        return self.config.get("api_url", DEFAULT_API_URL)

    @property
    def authenticator(self) -> BearerTokenAuthenticator:
        """Return the Bearer-token authenticator.

        Returns:
            An authenticator that injects ``Authorization: Bearer <key>``.
        """
        return BearerTokenAuthenticator.create_for_stream(
            self,
            token=self.config["api_key"],
        )

    @property
    def http_headers(self) -> dict:
        """Return the base HTTP headers.

        Returns:
            A dictionary of HTTP headers.
        """
        return {
            "User-Agent": f"{self.tap_name}/{self._tap.plugin_version}",
            "Accept": "application/json",
        }

    def _request(
        self,
        prepared_request: requests.PreparedRequest,
        context: Context | None,
    ) -> requests.Response:
        """Throttle to the account-level rate limit, then send the request.

        Args:
            prepared_request: The prepared HTTP request.
            context: The stream context.

        Returns:
            The HTTP response.
        """
        wait = REQUEST_INTERVAL_SECONDS - (
            time.monotonic() - RiversideStream._last_request_at
        )
        if wait > 0:
            time.sleep(wait)
        try:
            return super()._request(prepared_request, context)
        finally:
            RiversideStream._last_request_at = time.monotonic()

    def get_new_paginator(self) -> BaseAPIPaginator:
        """Create a new cursor pagination helper.

        Returns:
            A :class:`RiversidePaginator` instance.
        """
        return RiversidePaginator()

    def get_url_params(
        self,
        context: Context | None,  # noqa: ARG002
        next_page_token: t.Any | None,  # noqa: ANN401
    ) -> dict[str, t.Any]:
        """Return the base pagination query params.

        Args:
            context: The stream context.
            next_page_token: The next-page cursor, if any.

        Returns:
            A dictionary of URL query parameters.
        """
        params: dict[str, t.Any] = {
            "limit": self.config.get("page_size", DEFAULT_PAGE_SIZE),
        }
        if next_page_token:
            params["cursor"] = next_page_token
        return params

    def parse_response(self, response: requests.Response) -> t.Iterable[dict]:
        """Parse the response and return an iterator of result records.

        Args:
            response: The HTTP ``requests.Response`` object.

        Yields:
            Each record from the source.
        """
        yield from extract_jsonpath(
            self.records_jsonpath,
            input=response.json(parse_float=decimal.Decimal),
        )

    def post_process(
        self,
        row: dict,
        context: Context | None = None,  # noqa: ARG002
    ) -> dict | None:
        """As needed, append or transform raw data to match expected structure.

        Args:
            row: An individual record from the stream.
            context: The stream context.

        Returns:
            The updated record dictionary, or ``None`` to skip the record.
        """
        return row
