"""Tests for headless `main.py --live` startup. No network: Telegram is mocked."""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import main
from source.core.Bot import Bot
from source.core.Telegram import HeadlessStartupError, Telegram


def _creds(phone: str) -> MagicMock:
    creds = MagicMock()
    creds.api_id = 123456
    creds.api_hash = "secret_hash"
    creds.phone_number = phone
    return creds


def _write_forward_config(path: Path, entries: list[dict]) -> str:
    path.write_text(json.dumps(entries), encoding="utf-8")
    return str(path)


def _forward_entry(source_id: int, enabled: bool = True) -> dict:
    return {
        "sourceID": source_id,
        "sourceName": f"src{source_id}",
        "destinationID": 99,
        "destinationName": "dst",
        "start_date": "2026-01-01",
        "end_date": None,
        "timezone_name": "Asia/Tokyo",
        "dry_run": True,
        "enabled": enabled,
    }


def _mock_telegram_class() -> MagicMock:
    instance = MagicMock()
    instance.connect = AsyncMock()
    instance.start_forward_live = AsyncMock()
    instance.disconnect = AsyncMock()
    return MagicMock(return_value=instance)


class TestStartLiveErrors:
    """start_live must fail fast with HeadlessStartupError, never prompt."""

    @pytest.mark.asyncio
    async def test_no_credentials(self):
        with patch("source.core.Bot.Credentials") as mock_creds:
            mock_creds.get_all.return_value = []
            with pytest.raises(HeadlessStartupError, match="No credentials"):
                await Bot().start_live()

    @pytest.mark.asyncio
    async def test_unknown_account(self):
        with patch("source.core.Bot.Credentials") as mock_creds:
            mock_creds.get_all.return_value = [_creds("+111"), _creds("+222")]
            with pytest.raises(HeadlessStartupError, match=r"\+999 was not found"):
                await Bot().start_live("+999")

    @pytest.mark.asyncio
    async def test_multiple_accounts_without_account_flag(self):
        with patch("source.core.Bot.Credentials") as mock_creds:
            mock_creds.get_all.return_value = [_creds("+111"), _creds("+222")]
            with pytest.raises(HeadlessStartupError, match="--account"):
                await Bot().start_live()

    @pytest.mark.asyncio
    async def test_missing_config_file(self, tmp_path):
        with (
            patch("source.core.Bot.Credentials") as mock_creds,
            patch(
                "source.core.Bot.FORWARD_CONFIG_FILE_PATH",
                str(tmp_path / "missing.json"),
            ),
            patch("source.core.Bot.Telegram") as mock_tg,
        ):
            mock_creds.get_all.return_value = [_creds("+111")]
            with pytest.raises(HeadlessStartupError, match="Live Forward once"):
                await Bot().start_live()
            mock_tg.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_config(self, tmp_path):
        path = _write_forward_config(tmp_path / "fwd.json", [])
        with (
            patch("source.core.Bot.Credentials") as mock_creds,
            patch("source.core.Bot.FORWARD_CONFIG_FILE_PATH", path),
            patch("source.model.ForwardConfig.FORWARD_CONFIG_FILE_PATH", path),
            patch("source.core.Bot.Telegram") as mock_tg,
        ):
            mock_creds.get_all.return_value = [_creds("+111")]
            with pytest.raises(HeadlessStartupError, match="Live Forward once"):
                await Bot().start_live()
            mock_tg.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_configs_disabled(self, tmp_path):
        path = _write_forward_config(
            tmp_path / "fwd.json", [_forward_entry(1, enabled=False)]
        )
        with (
            patch("source.core.Bot.Credentials") as mock_creds,
            patch("source.core.Bot.FORWARD_CONFIG_FILE_PATH", path),
            patch("source.model.ForwardConfig.FORWARD_CONFIG_FILE_PATH", path),
            patch("source.core.Bot.Telegram") as mock_tg,
        ):
            mock_creds.get_all.return_value = [_creds("+111")]
            with pytest.raises(HeadlessStartupError, match="disabled"):
                await Bot().start_live()
            mock_tg.assert_not_called()


class TestStartLiveSuccess:
    @pytest.mark.asyncio
    async def test_single_account_auto_picked_and_config_map_passed(self, tmp_path):
        path = _write_forward_config(tmp_path / "fwd.json", [_forward_entry(1)])
        tg_cls = _mock_telegram_class()
        with (
            patch("source.core.Bot.Credentials") as mock_creds,
            patch("source.core.Bot.FORWARD_CONFIG_FILE_PATH", path),
            patch("source.model.ForwardConfig.FORWARD_CONFIG_FILE_PATH", path),
            patch("source.core.Bot.Telegram", tg_cls),
        ):
            mock_creds.get_all.return_value = [_creds("+111")]
            # The mocked forward returns, which start_live reports as a lost connection.
            with pytest.raises(ConnectionError):
                await Bot().start_live()

        tg_cls.assert_called_once()
        assert tg_cls.call_args.args[0].phone_number == "+111"
        instance = tg_cls.return_value
        instance.connect.assert_awaited_once_with(interactive=False)
        instance.start_forward_live.assert_awaited_once()
        config_map = instance.start_forward_live.call_args.args[0]
        assert list(config_map) == [1]
        assert config_map[1].dry_run is False
        assert config_map[1].timezone_name == "UTC"
        instance.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_explicit_account_selected(self, tmp_path):
        path = _write_forward_config(tmp_path / "fwd.json", [_forward_entry(1)])
        tg_cls = _mock_telegram_class()
        with (
            patch("source.core.Bot.Credentials") as mock_creds,
            patch("source.core.Bot.FORWARD_CONFIG_FILE_PATH", path),
            patch("source.model.ForwardConfig.FORWARD_CONFIG_FILE_PATH", path),
            patch("source.core.Bot.Telegram", tg_cls),
        ):
            mock_creds.get_all.return_value = [_creds("+111"), _creds("+222")]
            with pytest.raises(ConnectionError):
                await Bot().start_live("+222")
        assert tg_cls.call_args.args[0].phone_number == "+222"

    @pytest.mark.asyncio
    async def test_disconnect_raises_connection_error_and_still_disconnects(
        self, tmp_path
    ):
        path = _write_forward_config(tmp_path / "fwd.json", [_forward_entry(1)])
        tg_cls = _mock_telegram_class()
        # start_forward_live returning means the connection was lost.
        tg_cls.return_value.start_forward_live.return_value = None
        with (
            patch("source.core.Bot.Credentials") as mock_creds,
            patch("source.core.Bot.FORWARD_CONFIG_FILE_PATH", path),
            patch("source.model.ForwardConfig.FORWARD_CONFIG_FILE_PATH", path),
            patch("source.core.Bot.Telegram", tg_cls),
        ):
            mock_creds.get_all.return_value = [_creds("+111")]
            with pytest.raises(ConnectionError, match="Disconnected from Telegram"):
                await Bot().start_live()
        tg_cls.return_value.disconnect.assert_awaited_once()


class TestTelegramConnectInteractive:
    @pytest.mark.asyncio
    async def test_unauthorized_headless_raises_without_start(self):
        client = MagicMock()
        client.is_connected.return_value = False
        client.connect = AsyncMock()
        client.is_user_authorized = AsyncMock(return_value=False)
        client.start = AsyncMock()
        client.disconnect = AsyncMock()
        with patch("source.core.Telegram.TelegramClient", return_value=client):
            tg = Telegram(_creds("+111"))
            with pytest.raises(HeadlessStartupError, match="python main.py"):
                await tg.connect(interactive=False)
        client.start.assert_not_called()
        client.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_interactive_connect_still_calls_start(self):
        client = MagicMock()
        client.is_connected.return_value = False
        client.connect = AsyncMock()
        client.is_user_authorized = AsyncMock(return_value=False)
        client.start = AsyncMock()
        client.disconnect = AsyncMock()
        with patch("source.core.Telegram.TelegramClient", return_value=client):
            tg = Telegram(_creds("+111"))
            await tg.connect()
        client.start.assert_awaited_once_with("+111")


class TestMainExitCodes:
    def _run_main(self, argv: list[str], run_side_effect) -> object:
        with (
            patch.object(sys, "argv", ["main.py", *argv]),
            patch("main.run", side_effect=run_side_effect),
            patch("main.os.makedirs"),
        ):
            with pytest.raises(SystemExit) as exc:
                main.main()
        return exc.value.code

    def test_headless_error_exits_2(self):
        async def fail(live, account):
            raise HeadlessStartupError("nope")

        assert self._run_main(["--live"], fail) == 2

    def test_other_error_exits_1(self):
        async def fail(live, account):
            raise RuntimeError("network down")

        assert self._run_main(["--live"], fail) == 1

    def test_account_requires_live(self):
        with patch.object(sys, "argv", ["main.py", "--account", "+111"]):
            with pytest.raises(SystemExit) as exc:
                main.parse_args()
        assert exc.value.code == 2
