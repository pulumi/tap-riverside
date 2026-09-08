# tap-riverside

A [Singer](https://singer.io) tap for the
[Riverside (riverside.fm)](https://riverside.fm) Business API v3, built with
the [Meltano Singer SDK](https://sdk.meltano.com).

It pulls webinar registrants — including attendance (`participated`,
`duration`) and `utm` attribution — into your warehouse. Built for
[pulumi/data#953](https://github.com/pulumi/data/issues/953) as part of
replacing BigMarker.

## Requirements

A Riverside **Business API key** (Bearer token). The Business API is gated per
account — the key is issued by your Riverside customer success manager. One
key per account, shown once; **regenerating it revokes the previous key**, so
regenerating in Riverside settings breaks a running ingestion with no warning.

## Streams

| Stream | Endpoint | Notes |
| --- | --- | --- |
| `registrants` | `GET /api/v3/events/{event_id}/registrants` | One partition per configured `event_ids` entry. `event_id` FK added by the tap. |

### Why `event_ids` is a config setting

The Business API has **no route to list events** (`GET /events` is a 404), so
webinar discovery cannot happen through the API. The webinars to pull must be
supplied explicitly via `event_ids`. Adding a new webinar (or backfilling an
old one) means adding its id to the config.

### Replication semantics

- The `updated_after` query param filters **registration date only** and will
  not resurface a registrant whose attendance changed, so the tap re-pulls the
  full registrant list per event on every run. Deduplicate downstream
  (`key-properties: []` at the Meltano layer); the natural key is
  `(event_id, email)` — registrant objects carry no id.
- `duration` is `"00:00"` until the session ends and is populated (as
  **MM:SS**) ~30 seconds after — pull after the webinar has ended to capture
  attendance, and daily for upcoming events to capture registrations.
- `attendance_rate` **never populates for live webinars**; derive it
  downstream from `duration` ÷ event length.
- The API is rate limited to **1 request/second**; the tap throttles all
  requests accordingly. Cursor pagination, `limit` max 500.

## Configuration

| Setting | Required | Default | Description |
| --- | --- | --- | --- |
| `api_key` | yes | — | Riverside Business API key (Bearer token). |
| `api_url` | no | `https://platform.riverside.fm` | API base URL. |
| `event_ids` | yes | — | Webinar/event ids (24-char hex) to pull registrants for. |
| `page_size` | no | `500` | Records per page (max 500). |

Run `tap-riverside --about --format=markdown` for the full config reference.

## Usage

```bash
# with uv (recommended)
uv run tap-riverside --version
uv run tap-riverside --about --format=json

# discovery / sync (config.json holds api_key, event_ids)
uv run tap-riverside --config config.json --discover > catalog.json
uv run tap-riverside --config config.json
```

### With Meltano (local dev)

```bash
export TAP_RIVERSIDE_API_KEY='...'
export TAP_RIVERSIDE_EVENT_IDS='["6a973026993c7a02e8334525"]'
meltano install
meltano run tap-riverside target-jsonl
```

## Developing

```bash
uv sync
uv run --group test pytest
uvx ruff check .
```
