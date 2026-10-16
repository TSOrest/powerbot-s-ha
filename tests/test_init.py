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
    mock_api["send"].assert_any_await("111", protocol.start(3, 2), wait_timeout=15)

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
    mock_api["send"].assert_any_await("111", protocol.set_suction(3, 3), wait_timeout=15)
    assert hass.states.get("select.kitchen_water_level").state == "high"

    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.kitchen_carpet_mode"}, blocking=True)
    mock_api["send"].assert_any_await("111", protocol.carpet_mode(True), wait_timeout=15)
    assert hass.states.get("switch.kitchen_carpet_mode").state == "on"


async def test_paused_start_resumes(hass: HomeAssistant, mock_api) -> None:
    mock_api["state"].return_value = {"id": "111", "state": "pause", "batteryLevel": 50, "fanLevel": "2"}
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await hass.services.async_call("vacuum", "start", {"entity_id": "vacuum.kitchen"}, blocking=True)
    mock_api["send"].assert_any_await("111", protocol.resume(), wait_timeout=15)


async def test_settings_read_from_robot(hass: HomeAssistant, mock_api) -> None:
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("number.kitchen_volume").state == "99"
    assert hass.states.get("switch.kitchen_carpet_mode").state == "on"
    assert hass.states.get("switch.kitchen_do_not_disturb").state == "on"
    assert hass.states.get("time.kitchen_do_not_disturb_start").state == "22:00:00"
    assert hass.states.get("time.kitchen_do_not_disturb_end").state == "08:00:00"
    voice = hass.states.get("select.kitchen_voice")
    assert voice.state == "Українська"
    assert voice.attributes["options"] == ["English", "Українська"]
    # 4112 minutes used: filter 150 h, side brush 100 h, main brush 200 h
    assert hass.states.get("sensor.kitchen_filter").state == "54"
    assert hass.states.get("sensor.kitchen_side_brush").state == "31"
    assert hass.states.get("sensor.kitchen_main_brush").state == "65"
    mock_api["parts"].assert_awaited_with("111", "u1")
    assert hass.states.get("sensor.kitchen_cleaning_mode").state == "auto"
    assert hass.states.get("sensor.kitchen_cleaned_area").state == "0"
    assert hass.states.get("sensor.kitchen_cleaning_time").state == "0"
    assert hass.states.get("sensor.kitchen_error").state == "none"
    assert hass.states.get("sensor.kitchen_error_code") is None  # diagnostic, disabled by default


async def test_robot_not_answering_queries_keeps_entities_unknown(hass: HomeAssistant, mock_api) -> None:
    from custom_components.powerbot_s.api import PowerBotDeviceTimeoutError

    mock_api["send"].side_effect = PowerBotDeviceTimeoutError("timeout")
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("vacuum.kitchen").state == "docked"
    assert hass.states.get("number.kitchen_volume").state == "unknown"


async def test_locate_volume_voice_and_do_not_disturb(hass: HomeAssistant, mock_api) -> None:
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    send = mock_api["send"]

    await hass.services.async_call("vacuum", "locate", {"entity_id": "vacuum.kitchen"}, blocking=True)
    send.assert_any_await("111", protocol.locate(), wait_timeout=15)

    await hass.services.async_call(
        "number", "set_value", {"entity_id": "number.kitchen_volume", "value": 40}, blocking=True
    )
    send.assert_any_await("111", protocol.volume(40), wait_timeout=15)

    await hass.services.async_call(
        "select", "select_option", {"entity_id": "select.kitchen_voice", "option": "English"}, blocking=True
    )
    send.assert_any_await("111", protocol.select_voice(35), wait_timeout=15)
    assert hass.states.get("select.kitchen_voice").state == "English"

    # Do not disturb is on (read from the robot), so a new end time is sent right away
    await hass.services.async_call(
        "time", "set_value", {"entity_id": "time.kitchen_do_not_disturb_end", "time": "07:00:00"}, blocking=True
    )
    send.assert_any_await("111", protocol.do_not_disturb(True, (22, 0), (7, 0)), wait_timeout=15)

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.kitchen_do_not_disturb"}, blocking=True
    )
    send.assert_any_await("111", protocol.do_not_disturb(False, (22, 0), (7, 0)), wait_timeout=15)
    assert hass.states.get("switch.kitchen_do_not_disturb").state == "off"

    # While it is off, a new start time is only stored
    send.reset_mock()
    await hass.services.async_call(
        "time", "set_value", {"entity_id": "time.kitchen_do_not_disturb_start", "time": "23:30:00"}, blocking=True
    )
    assert all(call.kwargs["wait_timeout"] != 15 for call in send.await_args_list)
    assert hass.states.get("time.kitchen_do_not_disturb_start").state == "23:30:00"


async def test_device_shows_model(hass: HomeAssistant, mock_api) -> None:
    from homeassistant.helpers import device_registry as dr

    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "111")})
    assert device.model == "VR7700"
    assert device.model_id == "610VR510"


async def test_other_model_is_read_only(hass: HomeAssistant, mock_api) -> None:
    from homeassistant.helpers import issue_registry as ir

    from .conftest import DEVICE

    mock_api["devices"].return_value = [
        {**DEVICE, "product": {"sn8": "610VR700", "productModel": "S9", "protoVersion": 1}}
    ]
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    vacuum = hass.states.get("vacuum.kitchen")
    assert vacuum.state == "docked"
    assert vacuum.attributes["supported_features"] == 4096  # state only
    assert hass.states.get("sensor.kitchen_battery").state == "87"
    for entity_id in ("number.kitchen_volume", "select.kitchen_water_level", "switch.kitchen_carpet_mode",
                      "sensor.kitchen_filter", "sensor.kitchen_cleaning_mode"):
        assert hass.states.get(entity_id) is None
    # No query frames are sent to a robot whose command set is unknown
    mock_api["send"].assert_not_awaited()
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "unsupported_model_111")
    assert issue.translation_placeholders["sn8"] == "610VR700"


async def test_no_water_level_without_mop(hass: HomeAssistant, mock_api) -> None:
    from .conftest import REPLIES

    reply = bytearray.fromhex(REPLIES[protocol.query_work_state()])
    reply[27] &= 0xFE  # has_mop bit cleared
    replies = {**REPLIES, protocol.query_work_state(): reply.hex()}

    async def send(device_id, frame, wait_timeout=None):
        return replies.get(frame)

    mock_api["send"].side_effect = send
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("select.kitchen_water_level") is None
    assert hass.states.get("select.kitchen_voice") is not None


async def test_schedule_switch(hass: HomeAssistant, mock_api) -> None:
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    schedule = hass.states.get("switch.kitchen_schedule_1")
    assert schedule.state == "off"
    assert schedule.attributes["start"] == "10:00"
    assert schedule.attributes["days"] == ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    assert schedule.attributes["cleaning_mode"] == "auto"

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.kitchen_schedule_1"}, blocking=True
    )
    mock_api["send"].assert_any_await("111", protocol.schedule_enabled(1, True), wait_timeout=15)
    assert hass.states.get("switch.kitchen_schedule_1").state == "on"


async def test_move_and_clean_modes(hass: HomeAssistant, mock_api) -> None:
    import pytest
    from unittest.mock import patch

    from homeassistant.exceptions import ServiceValidationError

    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch("custom_components.powerbot_s.vacuum.asyncio.sleep") as sleep:
        await hass.services.async_call(
            "vacuum",
            "send_command",
            {"entity_id": "vacuum.kitchen", "command": "move", "params": {"direction": "left", "duration": 9}},
            blocking=True,
        )
    sleep.assert_awaited_once_with(5.0)
    sent = [c.args[1] for c in mock_api["send"].await_args_list]
    assert sent.index(protocol.manual(3)) < sent.index(protocol.manual(0))

    await hass.services.async_call(
        "vacuum", "send_command", {"entity_id": "vacuum.kitchen", "command": "clean_edge"}, blocking=True
    )
    mock_api["send"].assert_any_await("111", protocol.start(3, 2, mode=3), wait_timeout=15)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "vacuum", "send_command", {"entity_id": "vacuum.kitchen", "command": "dance"}, blocking=True
        )


async def test_suction_select(hass: HomeAssistant, mock_api) -> None:
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    suction = hass.states.get("select.kitchen_suction_power")
    assert suction.state == "turbo"
    await hass.services.async_call(
        "select", "select_option", {"entity_id": "select.kitchen_suction_power", "option": "max"}, blocking=True
    )
    # Suction and water go together; water keeps its current level (normal)
    mock_api["send"].assert_any_await("111", protocol.set_suction(5, 2), wait_timeout=15)


async def test_child_lock_history_and_firmware(hass: HomeAssistant, mock_api) -> None:
    from homeassistant.helpers import device_registry as dr, entity_registry as er

    await hass.config.async_set_time_zone("UTC")
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # The recorded work-state reply has byte 46 = 0
    assert hass.states.get("switch.kitchen_child_lock").state == "off"
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.kitchen_child_lock"}, blocking=True
    )
    mock_api["send"].assert_any_await("111", protocol.child_lock(True), wait_timeout=15)
    assert hass.states.get("switch.kitchen_child_lock").state == "on"

    assert hass.states.get("sensor.kitchen_total_cleaning_time").state == "10.0"
    assert hass.states.get("sensor.kitchen_total_cleaned_area").state == "250.0"
    assert hass.states.get("sensor.kitchen_total_cleanings").state == "12"
    assert hass.states.get("sensor.kitchen_last_clean").state == "2026-10-15T10:00:00+00:00"
    firmware = hass.states.get("update.kitchen_firmware")
    assert firmware.state == "off"
    assert firmware.attributes["installed_version"] == "1.0.26"
    module = hass.states.get("update.kitchen_wi_fi_module_firmware")
    assert module.state == "on"
    assert module.attributes["installed_version"] == "3.1.5"
    assert module.attributes["latest_version"] == "new"
    assert hass.states.get("sensor.kitchen_since_sensor_cleaning").state == "68.5"
    # SSID and IP are personal network details, so they start disabled
    registry = er.async_get(hass)
    for entity_id in ("sensor.kitchen_wi_fi_network", "sensor.kitchen_ip_address"):
        assert hass.states.get(entity_id) is None
        assert registry.async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.config_entries.async_entries("powerbot_s")[0].runtime_data.wifi == protocol.WifiInfo(
        "192.168.1.50", "Home", -55
    )
    assert hass.states.get("sensor.kitchen_signal_strength").state == "-55"
    assert hass.states.get("binary_sensor.kitchen_automatic_firmware_updates").state == "on"
    device = dr.async_get(hass).async_get_device(identifiers={("powerbot_s", "111")})
    assert device.sw_version == "1.0.26"
