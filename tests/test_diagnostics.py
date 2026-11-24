"""Diagnostics retain useful BLE errors without exposing addresses or packets."""

from custom_components.daybetter_led.diagnostics import exception_summary


def test_exception_summary_redacts_device_addresses_and_packet_bytes():
    error = OSError(
        "connection dropped for AA:BB:CC:DD:EE:FF; packet a1 10 11 01 14 ff 64"
    )

    summary = exception_summary(error)

    assert summary.startswith("OSError: connection dropped for")
    assert "AA:BB:CC:DD:EE:FF" not in summary
    assert "a1 10 11 01 14 ff 64" not in summary
    assert "<redacted address>" in summary
    assert "<redacted data>" in summary
