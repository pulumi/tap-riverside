"""Stream type classes for tap-riverside.

Field names mirror the Riverside Business API v3 (verified against live
responses; see pulumi/data#953). The API has **no route to list events** --
``GET /events`` is a 404 -- so the webinars to pull are supplied via the
``event_ids`` config setting and each becomes a partition of the registrants
stream.

The ``updated_after`` query param filters on registration date only and will
not resurface a registrant whose attendance changed, so the stream replicates
the full list per event on every run and is deduplicated downstream (matching
the house convention of ``key-properties: []`` at the Meltano layer).

Attendance caveats (verified live): ``duration`` is ``"00:00"`` until the
session ends and is populated (MM:SS) ~30s after; ``attendance_rate`` never
populates for live webinars -- derive it downstream from ``duration`` divided
by event length. Registrant objects carry no id; (event_id, email) is the
natural key.
"""

from __future__ import annotations

import typing as t

from singer_sdk import typing as th

from tap_riverside.client import RiversideStream

if t.TYPE_CHECKING:
    from singer_sdk.helpers.types import Context

# custom_fields vary per webinar; pass them through untyped so nothing is lost.
_PASSTHROUGH_OBJECT = th.ObjectType(additional_properties=True)


class RegistrantsStream(RiversideStream):
    """Registrants (and their attendance) for each configured webinar.

    One partition per ``event_ids`` entry. Supplies the fields only the API
    has: ``participated``, attendance ``duration`` and ``utm``.
    """

    name = "registrants"
    path = "/api/v3/events/{event_id}/registrants"
    primary_keys = ("event_id", "email")
    replication_key = None

    schema = th.PropertiesList(
        th.Property(
            "event_id",
            th.StringType,
            required=True,
            description="Webinar/event id (24-char hex, added by the tap from config).",
        ),
        th.Property("email", th.StringType, required=True),
        th.Property("first_name", th.StringType(nullable=True)),
        th.Property("last_name", th.StringType(nullable=True)),
        th.Property("registered_at", th.DateTimeType(nullable=True)),
        th.Property("approved", th.BooleanType(nullable=True)),
        th.Property(
            "join_url",
            th.StringType(nullable=True),
            description="Personalized audience join URL.",
        ),
        th.Property(
            "participated",
            th.BooleanType(nullable=True),
            description="True once the registrant watched >10s; flips mid-session.",
        ),
        th.Property(
            "attendance_rate",
            th.NumberType(nullable=True),
            description=(
                "Never populates for live webinars; derive from duration / event "
                "length downstream."
            ),
        ),
        th.Property(
            "duration",
            th.StringType(nullable=True),
            description=(
                "Attendance duration as MM:SS; 00:00 until ~30s after the session "
                "ends. Parsed in staging."
            ),
        ),
        th.Property("referrer", th.StringType(nullable=True)),
        th.Property(
            "utm",
            th.ObjectType(
                th.Property("source", th.StringType(nullable=True)),
                th.Property("medium", th.StringType(nullable=True)),
                th.Property("campaign", th.StringType(nullable=True)),
                th.Property("term", th.StringType(nullable=True)),
                th.Property("content", th.StringType(nullable=True)),
            ),
        ),
        th.Property("custom_fields", _PASSTHROUGH_OBJECT),
    ).to_dict()

    @property
    def partitions(self) -> list[dict] | None:
        """Return one partition per configured webinar id.

        Returns:
            A list of ``{"event_id": ...}`` contexts, one per ``event_ids``
            entry.
        """
        return [{"event_id": event_id} for event_id in self.config["event_ids"]]

    def post_process(
        self,
        row: dict,
        context: Context | None = None,
    ) -> dict | None:
        """Stamp the partition's event id onto each registrant record.

        Args:
            row: A registrant record.
            context: The partition context carrying ``event_id``.

        Returns:
            The record with ``event_id`` populated.
        """
        row["event_id"] = (context or {}).get("event_id")
        return row
