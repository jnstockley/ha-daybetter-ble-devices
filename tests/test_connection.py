"""Connection ownership must survive repeated advertisements and unload."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.daybetter_led.connection import DaybetterConnection


@pytest.fixture
def session():
    strip = SimpleNamespace(
        connected=False,
        update_device=AsyncMock(),
        disconnect=AsyncMock(),
    )
    return DaybetterConnection(strip)


async def test_connected_advertisements_do_not_reconnect(session):
    session.device.connected = True
    await session.async_update(SimpleNamespace(device="radio", advertisement="ad"))
    session.device.update_device.assert_not_awaited()


async def test_overlapping_advertisements_are_coalesced(session):
    started = asyncio.Event()
    finish = asyncio.Event()

    async def connect(*args):
        started.set()
        await finish.wait()

    session.device.update_device.side_effect = connect
    info = SimpleNamespace(device="radio", advertisement="ad")
    first = asyncio.create_task(session.async_update(info))
    await started.wait()
    await session.async_update(info)
    finish.set()
    await first
    session.device.update_device.assert_awaited_once_with("radio", "ad")


async def test_close_cancels_connection_before_disconnect(session):
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def connect(*args):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    async def disconnect():
        assert cancelled.is_set()

    session.device.update_device.side_effect = connect
    session.device.disconnect.side_effect = disconnect
    task = asyncio.create_task(
        session.async_update(SimpleNamespace(device=1, advertisement=2))
    )
    await started.wait()
    await session.async_close()
    assert task.cancelled()
    await session.async_update(SimpleNamespace(device=1, advertisement=2))
    assert session.device.update_device.await_count == 1
