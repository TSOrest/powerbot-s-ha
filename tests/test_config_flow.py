"""Config flow tests."""
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.powerbot_s.api import PowerBotAuthError
from custom_components.powerbot_s.const import CONF_DEVICE_ID, DOMAIN

CREDS = {"email": "a@b.c", "password": "pw"}


async def _start(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_single_robot_added_without_extra_steps(hass: HomeAssistant, mock_api) -> None:
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CREDS)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Kitchen"
    assert result["data"][CONF_DEVICE_ID] == "111"
    assert result["result"].unique_id == "111"


async def test_choose_between_robots(hass: HomeAssistant, mock_api) -> None:
    mock_api["devices"].return_value = [
        {"deviceId": "111", "nickname": "Kitchen"},
        {"deviceId": "222", "nickname": "Bedroom"},
    ]
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CREDS)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_device"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_DEVICE_ID: "222"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Bedroom"


async def test_invalid_auth(hass: HomeAssistant, mock_api) -> None:
    mock_api["login"].side_effect = PowerBotAuthError("nope")
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CREDS)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_empty_device_list_falls_back_to_manual(hass: HomeAssistant, mock_api) -> None:
    mock_api["devices"].return_value = []
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CREDS)
    assert result["step_id"] == "manual"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_DEVICE_ID: " 111 "})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DEVICE_ID] == "111"


async def test_already_configured(hass: HomeAssistant, mock_api) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id="111", data={**CREDS, CONF_DEVICE_ID: "111"}).add_to_hass(hass)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CREDS)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth(hass: HomeAssistant, mock_api) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id="111", data={**CREDS, CONF_DEVICE_ID: "111"})
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"email": "a@b.c", "password": "new"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["password"] == "new"
