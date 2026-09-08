"""Tests standard tap features using the built-in SDK tests library."""

from singer_sdk.testing import get_tap_test_class

from tap_riverside.tap import TapRiverside

SAMPLE_CONFIG = {
    "api_key": "DUMMY_API_KEY",
    "event_ids": ["6a973026993c7a02e8334525"],
}


# Run standard built-in tap tests from the SDK. Offline tests (config schema,
# discovery) run without credentials; tests that require a live connection use a
# real key passed via TAP_RIVERSIDE_* environment variables (see tox.ini).
TestTapRiverside = get_tap_test_class(
    tap_class=TapRiverside,
    config=SAMPLE_CONFIG,
)
