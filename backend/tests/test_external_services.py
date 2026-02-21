import sys
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Ensure backend is in path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.external import validate_cpf

@pytest.mark.asyncio
async def test_validate_cpf_mocked():
    """
    Test validate_cpf from external.py with mocked httpx.
    """
    with patch("httpx.AsyncClient") as MockClient:
        # Mock the context manager
        mock_instance = MockClient.return_value
        mock_instance.__aenter__.return_value = mock_instance

        # Configure the get method to be an async mock
        mock_instance.get = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_instance.get.return_value = mock_response

        # Test valid CPF
        result = await validate_cpf("12345678909")
        assert result is True

        # Test invalid length
        result = await validate_cpf("123")
        assert result is False

        # Mock failure response
        mock_response.status_code = 404
        result = await validate_cpf("12345678909")
        assert result is False

@pytest.mark.asyncio
async def test_fetch_brasil_api_data_mocked():
    """
    Test fetch_brasil_api_data from enrichment.py with mocked httpx.
    """
    from services.enrichment import fetch_brasil_api_data

    with patch("httpx.AsyncClient") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.__aenter__.return_value = mock_instance

        # Configure the get method
        mock_instance.get = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200

        # IMPORTANT: .json() is a synchronous method on the response object
        mock_response.json.return_value = {"name": "Test User", "cpf": "12345678909"}

        mock_instance.get.return_value = mock_response

        result = await fetch_brasil_api_data("12345678909")
        assert result == {"name": "Test User", "cpf": "12345678909"}

        # Mock failure response
        mock_response.status_code = 404
        result = await fetch_brasil_api_data("12345678909")
        assert result is None
