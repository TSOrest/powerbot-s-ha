"""Setup and entity tests."""
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.powerbot_s.api import PowerBotAuthError
from custom_components.powerbot_s.const import CONF_DEVICE_ID, DOMAIN
from custom_components.powerbot_s import protocol


def _entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Kitchen",
        unique_id="111",
        data={"email": "a@b.c", "password": "pw", CONF_DEVICE_ID: "111", "region": "eu"},
    )
    entry.add_to_hass(hass)
    return entry


async def test_setup_creates_entities(hass: HomeAssistant, mock_api) -> None:
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    vacuum = hass.states.get("vacuum.kitchen")
    assert vacuum.state == "docked"
    assert vacuum.attributes["fan_speed"] == "turbo"
    assert hass.states.get("sensor.kitchen_battery").state == "87"
    assert hass.states.get("sensor.kitchen_fan_speed").state == "turbo"
    assert hass.states.get("sensor.kitchen_status").state == "charging_finish"
    assert hass.states.get("binary_sensor.kitchen_docked").state == "on"
    assert hass.states.get("binary_sensor.kitchen_cleaning").state == "off"

    await hass.services.async_call("vacuum", "start", {"entity_id": "vacuum.kitchen"}, blocking=True)
    # Docked robot: a fresh auto clean with current suction (turbo) and default water (normal)
    mock_api["send"].assert_awaited_with("111", protocol.start(3, 2), wait_timeout=15)

    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_auth_failure_starts_reauth(hass: HomeAssistant, mock_api) -> None:
    mock_api["state"].side_effect = PowerBotAuthError("expired")
    entry = _entry(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert any(f["context"]["source"] == "reauth" for f in hass.config_entries.flow.async_progress())


async def test_robot_not_responding_has_clear_error(hass: HomeAssistant, mock_api) -> None:
    import pytest
    from homeassistant.exceptions import HomeAssistantError

    from custom_components.powerbot_s.api import PowerBotDeviceTimeoutError

    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    mock_api["send"].side_effect = PowerBotDeviceTimeoutError("API error 0080005: device response timeout")
    with pytest.raises(HomeAssistantError, match="did not respond"):
        await hass.services.async_call("vacuum", "start", {"entity_id": "vacuum.kitchen"}, blocking=True)


async def test_returning_to_dock_is_not_docked(hass: HomeAssistant, mock_api) -> None:
    mock_api["state"].return_value = {"id": "111", "state": "charging_back", "batteryLevel": 50}
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("vacuum.kitchen").state == "returning"
    assert hass.states.get("binary_sensor.kitchen_docked").state == "off"


async def test_water_level_and_carpet(hass: HomeAssistant, mock_api) -> None:
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "select", "select_option", {"entity_id": "select.kitchen_water_level", "option": "high"}, blocking=True
    )
    mock_api["send"].assert_awaited_with("111", protocol.set_suction(3, 3), wait_timeout=15)
    assert hass.states.get("select.kitchen_water_level").state == "high"

    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.kitchen_carpet_mode"}, blocking=True)
    mock_api["send"].assert_awaited_with("111", protocol.carpet_mode(True), wait_timeout=15)
    assert hass.states.get("switch.kitchen_carpet_mode").state == "on"


async def test_paused_start_resumes(hass: HomeAssistant, mock_api) -> None:
    mock_api["state"].return_value = {"id": "111", "state": "pause", "batteryLevel": 50, "fanLevel": "2"}
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await hass.services.async_call("vacuum", "start", {"entity_id": "vacuum.kitchen"}, blocking=True)
    mock_api["send"].assert_awaited_with("111", protocol.resume(), wait_timeout=15)


async def test_locate_volume_and_do_not_disturb(hass: HomeAssistant, mock_api) -> None:
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    send = mock_api["send"]

    await hass.services.async_call("vacuum", "locate", {"entity_id": "vacuum.kitchen"}, blocking=True)
    send.assert_awaited_with("111", protocol.locate(), wait_timeout=15)

    await hass.services.async_call(
        "number", "set_value", {"entity_id": "number.kitchen_volume", "value": 40}, blocking=True
    )
    send.assert_awaited_with("111", protocol.volume(40), wait_timeout=15)
    assert hass.states.get("number.kitchen_volume").state == "40"

    # While do not disturb is off, a new start time is only stored
    send.reset_mock()
    await hass.services.async_call(
        "time", "set_value", {"entity_id": "time.kitchen_do_not_disturb_start", "time": "23:30:00"}, blocking=True
    )
    send.assert_not_awaited()
    assert hass.states.get("time.kitchen_do_not_disturb_start").state == "23:30:00"

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.kitchen_do_not_disturb"}, blocking=True
    )
    send.assert_awaited_with("111", protocol.do_not_disturb(True, (23, 30), (8, 0)), wait_timeout=15)
    assert hass.states.get("switch.kitchen_do_not_disturb").state == "on"

    # While it is on, changing a time is sent right away
    await hass.services.async_call(
        "time", "set_value", {"entity_id": "time.kitchen_do_not_disturb_end", "time": "07:00:00"}, blocking=True
    )
    send.assert_awaited_with("111", protocol.do_not_disturb(True, (23, 30), (7, 0)), wait_timeout=15)
