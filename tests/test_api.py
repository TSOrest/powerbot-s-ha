"""Cloud client tests."""
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.powerbot_s.api import PowerBotApiClient, PowerBotAuthError
from custom_components.powerbot_s.const import CLIENT_ID, REGION_HOSTS

EU = REGION_HOSTS["eu"]
NA = REGION_HOSTS["na"]
LOGIN = f"/auth/login/email-password?clientId={CLIENT_ID}"


async def test_login_moves_to_account_region(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(f"{EU}{LOGIN}", json={"errorCode": "0051204"})
    aioclient_mock.post(f"{NA}{LOGIN}", json={"errorCode": "0", "data": {"accessToken": "a", "refreshToken": "r"}})
    saved = []
    client = PowerBotApiClient(async_get_clientsession(hass), "a@b.c", "pw", on_tokens_updated=saved.append)
    await client.async_login()
    assert client.get_tokens() == {"access_token": "a", "refresh_token": "r", "region": "na"}
    assert saved[-1]["region"] == "na"


async def test_wrong_password(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(f"{EU}{LOGIN}", json={"errorCode": "0051004", "msg": "bad"})
    client = PowerBotApiClient(async_get_clientsession(hass), "a@b.c", "pw")
    with pytest.raises(PowerBotAuthError):
        await client.async_login()


async def test_state_refreshes_expired_token(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(f"{EU}/shadow/device/state", status=401)
    aioclient_mock.get(
        f"{EU}/auth/refresh-token", json={"errorCode": "0", "data": {"accessToken": "new", "refreshToken": "r2"}}
    )
    client = PowerBotApiClient(
        async_get_clientsession(hass), "a@b.c", "pw", access_token="old", refresh_token="r"
    )
    with pytest.raises(PowerBotAuthError):
        # the mock keeps answering 401, so the retry fails too
        await client.async_get_device_state("111")
    assert client.get_tokens()["access_token"] == "new"


async def test_command_waits_longer_than_server_timeout(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(f"{EU}/devices/commands/111", json={"errorCode": "0"})
    client = PowerBotApiClient(async_get_clientsession(hass), "a@b.c", "pw", access_token="t")
    seen = {}
    real = client._raw_request

    async def spy(method, url, timeout=None, **kwargs):
        seen["timeout"] = timeout
        return await real(method, url, timeout=timeout, **kwargs)

    client._raw_request = spy
    await client.async_send_command("111", "AA", wait_timeout=30)
    assert seen["timeout"].total > 30
    assert aioclient_mock.mock_calls[-1][2] == {"data": "AA", "waitTimeoutInSeconds": 30}


async def test_timeout_is_reported_clearly(hass: HomeAssistant, aioclient_mock) -> None:
    from custom_components.powerbot_s.api import PowerBotApiError

    aioclient_mock.post(f"{EU}/devices/commands/111", exc=TimeoutError())
    client = PowerBotApiClient(async_get_clientsession(hass), "a@b.c", "pw", access_token="t")
    with pytest.raises(PowerBotApiError, match="Timed out after 45s"):
        await client.async_send_command("111", "AA", wait_timeout=30)


async def test_device_timeout_code(hass: HomeAssistant, aioclient_mock) -> None:
    from custom_components.powerbot_s.api import PowerBotDeviceTimeoutError

    aioclient_mock.post(
        f"{EU}/devices/commands/111", json={"errorCode": "0080005", "msg": "device response timeout"}
    )
    client = PowerBotApiClient(async_get_clientsession(hass), "a@b.c", "pw", access_token="t")
    with pytest.raises(PowerBotDeviceTimeoutError):
        await client.async_send_command("111", "AA", wait_timeout=30)


async def test_query_returns_robot_reply(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(
        f"{EU}/devices/commands/111",
        json={"errorCode": "0", "data": {"deviceId": "111", "data": "aa0cb800000000000103368082", "version": 1}},
    )
    client = PowerBotApiClient(async_get_clientsession(hass), "a@b.c", "pw", access_token="t")
    assert await client.async_send_command("111", "AA0BB8000000000000033604", wait_timeout=5) == (
        "aa0cb800000000000103368082"
    )


async def test_parts_and_voices_from_midea(hass: HomeAssistant, aioclient_mock) -> None:
    from custom_components.powerbot_s.api import PowerBotApiError
    from custom_components.powerbot_s.const import PARTS_HOSTS

    host = PARTS_HOSTS["eu"]
    aioclient_mock.post(
        f"{host}/v2/app2pro/m7/parts/info", json={"errorCode": "0", "data": {"filter_net_time": "4112"}}
    )
    aioclient_mock.get(
        f"{host}/v2/app2pro/m7/voice/list", json={"code": "0", "data": [{"id": 35, "title": "English"}]}
    )
    client = PowerBotApiClient(async_get_clientsession(hass), "a@b.c", "pw", access_token="t")
    assert await client.async_get_parts("111", "u1") == {"filter_net_time": "4112"}
    assert aioclient_mock.mock_calls[-1][2] == {"deviceId": "111", "userId": "u1"}
    assert await client.async_get_voices("610VR510") == [{"id": 35, "title": "English"}]

    aioclient_mock.clear_requests()
    aioclient_mock.post(
        f"{host}/v2/app2pro/m7/parts/info", json={"errorCode": "3102", "msg": "The user does not exist."}
    )
    with pytest.raises(PowerBotApiError, match="3102"):
        await client.async_get_parts("111", "")
