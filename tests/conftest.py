"""Pytest configuration and fixtures for Telegram Forwarder Bot tests."""

import asyncio
import os
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def mock_console() -> Generator[MagicMock, None, None]:
    """Mock the console to prevent output during tests."""
    with pytest.MonkeyPatch().context() as m:
        mock_console = MagicMock()
        m.setattr("source.utils.Console.Terminal.console", mock_console)
        yield mock_console


@pytest.fixture
def temp_resources_dir(tmp_path: Path) -> Path:
    """Create a temporary resources directory for tests."""
    resources_dir = tmp_path / "resources"
    resources_dir.mkdir()
    return resources_dir


@pytest.fixture
def mock_telegram_client() -> AsyncMock:
    """Create a mock Telegram client for testing."""
    client = AsyncMock()
    client.connect = AsyncMock(return_value=True)
    client.is_user_authorized = AsyncMock(return_value=True)
    client.start = AsyncMock()
    client.disconnect = AsyncMock()
    client.get_me = AsyncMock(return_value=MagicMock(id=12345, username="test_user"))
    return client


@pytest.fixture
def mock_credentials() -> MagicMock:
    """Create mock credentials for testing."""
    creds = MagicMock()
    creds.api_id = 123456
    creds.api_hash = "test_hash"
    creds.phone_number = "+1234567890"
    return creds


@pytest.fixture
def sample_credentials() -> dict[str, Any]:
    """Sample credentials for testing."""
    return {
        "api_id": 123456,
        "api_hash": "test_hash_123",
        "phone_number": "+1234567890",
    }


@pytest.fixture
def sample_chat() -> dict[str, Any]:
    """Sample chat data for testing."""
    return {
        "id": -1001234567890,
        "title": "Test Group",
        "type": "Group",
        "username": None,
    }


@pytest.fixture
def sample_forward_config() -> dict[str, Any]:
    """Sample forward configuration for testing."""
    return {
        "source_id": -1001234567890,
        "source_name": "Source Chat",
        "destination_id": -1000987654321,
        "destination_name": "Destination Chat",
        "enabled": True,
    }


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment() -> None:
    """Set up test environment variables."""
    os.environ.setdefault("TELEGRAM_API_ID", "123456")
    os.environ.setdefault("TELEGRAM_API_HASH", "test_hash")
    os.environ.setdefault("LOG_LEVEL", "DEBUG")


# Custom markers
def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "asyncio: marks tests as async tests")
