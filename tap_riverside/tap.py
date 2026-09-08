"""Riverside tap class."""

from __future__ import annotations

from singer_sdk import Tap
from singer_sdk import typing as th

from tap_riverside import streams


class TapRiverside(Tap):
    """Singer tap for Riverside (riverside.fm) webinar data."""

    name = "tap-riverside"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "api_key",
            th.StringType(nullable=False),
            required=True,
            secret=True,
            title="API Key",
            description=(
                "Riverside Business API key, sent as a Bearer token. Gated per "
                "account (issued by the Riverside customer success manager); "
                "one key per account, and regenerating it revokes the previous "
                "one."
            ),
        ),
        th.Property(
            "api_url",
            th.StringType(nullable=False),
            default="https://platform.riverside.fm",
            title="API URL",
            description="Base URL for the Riverside Business API.",
        ),
        th.Property(
            "event_ids",
            th.ArrayType(th.StringType),
            required=True,
            title="Event IDs",
            description=(
                "Webinar/event ids (24-char hex) to pull registrants for. The "
                "API has no route to list events, so ids must be supplied "
                "explicitly."
            ),
        ),
        th.Property(
            "page_size",
            th.IntegerType(nullable=True),
            default=500,
            title="Page Size",
            description="Number of records to request per page (max 500).",
        ),
        additional_properties=False,
    ).to_dict()

    def discover_streams(self) -> list[streams.RiversideStream]:
        """Return a list of discovered streams.

        Returns:
            A list of Riverside streams.
        """
        return [
            streams.RegistrantsStream(self),
        ]


if __name__ == "__main__":
    TapRiverside.cli()
