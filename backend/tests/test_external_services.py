import pytest
from unittest.mock import patch, MagicMock, AsyncMock
# Import the module to ensure it's loaded
import services.external
from services.external import validate_cpf, fetch_brasil_api_data

@pytest.mark.asyncio
async def test_validate_cpf_mocked():
    """
    Test validate_cpf from external.py with mocked httpx.
    """
    # Patch httpx in the services.external module
    with patch("services.external.httpx") as MockHttpx:
        MockClient = MockHttpx.AsyncClient

        # Mock the instance returned by AsyncClient()
        mock_instance = MockClient.return_value

        # Mock context manager methods
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)

        # Configure the get method
        mock_instance.get = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"valid": True}

        mock_instance.get.return_value = mock_response

        # Test valid CPF
        result = await validate_cpf("12345678909")
        assert result is True

@pytest.mark.asyncio
async def test_fetch_brasil_api_data_mocked():
    """
    Test fetch_brasil_api_data
    """
    with patch("services.external.httpx") as MockHttpx:
        MockClient = MockHttpx.AsyncClient
        mock_instance = MockClient.return_value

        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)

        mock_instance.get = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "Test User", "cpf": "12345678909"}
        mock_instance.get.return_value = mock_response

        result = await fetch_brasil_api_data("12345678909")
        assert result == {"name": "Test User", "cpf": "12345678909"}
