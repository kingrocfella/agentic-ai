"""Unit tests for the weather tool."""

from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

from app.tools.ollama_tools import (
    get_weather_by_city,
    _format_current_weather,
    _format_historical_weather,
    _format_forecast_weather,
)


# =============================================================================
# Mock Data
# =============================================================================


def _mock_current_response() -> dict:
    """Mock response for current weather API."""
    return {
        "location": {
            "name": "London",
            "country": "United Kingdom",
        },
        "current": {
            "temp_c": 15.0,
            "temp_f": 59.0,
            "condition": {"text": "Partly cloudy"},
            "humidity": 72,
            "wind_kph": 12.0,
            "wind_dir": "SW",
            "feelslike_c": 14.0,
        },
    }


def _mock_forecast_response() -> dict:
    """Mock response for forecast weather API."""
    return {
        "location": {
            "name": "London",
            "country": "United Kingdom",
        },
        "forecast": {
            "forecastday": [
                {
                    "day": {
                        "maxtemp_c": 18.0,
                        "maxtemp_f": 64.4,
                        "mintemp_c": 12.0,
                        "mintemp_f": 53.6,
                        "avgtemp_c": 15.0,
                        "avgtemp_f": 59.0,
                        "condition": {"text": "Sunny"},
                        "maxwind_kph": 20.0,
                        "avghumidity": 65,
                        "daily_chance_of_rain": 10,
                        "daily_chance_of_snow": 0,
                    }
                }
            ]
        },
    }


def _mock_history_response() -> dict:
    """Mock response for historical weather API."""
    return {
        "location": {
            "name": "London",
            "country": "United Kingdom",
        },
        "forecast": {
            "forecastday": [
                {
                    "day": {
                        "maxtemp_c": 20.0,
                        "maxtemp_f": 68.0,
                        "mintemp_c": 14.0,
                        "mintemp_f": 57.2,
                        "avgtemp_c": 17.0,
                        "avgtemp_f": 62.6,
                        "condition": {"text": "Clear"},
                        "maxwind_kph": 15.0,
                        "totalprecip_mm": 0.0,
                        "avghumidity": 60,
                    }
                }
            ]
        },
    }


# =============================================================================
# Current Weather Tests
# =============================================================================


def test_get_current_weather_success() -> None:
    """Test fetching current weather successfully."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = _mock_current_response()

    with patch("app.tools.ollama_tools.httpx.get", return_value=mock_response):
        with patch("app.tools.ollama_tools.WEATHER_API_KEY", "test-key"):
            result = get_weather_by_city.invoke({"city": "London"})

    assert "Current Weather in London" in result
    assert "15.0°C" in result
    assert "Partly cloudy" in result


def test_get_current_weather_no_date() -> None:
    """Test that no date parameter returns current weather."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = _mock_current_response()

    with patch(
        "app.tools.ollama_tools.httpx.get", return_value=mock_response
    ) as mock_get:
        with patch("app.tools.ollama_tools.WEATHER_API_KEY", "test-key"):
            get_weather_by_city.invoke({"city": "London"})

    # Verify current.json endpoint was called
    call_args = mock_get.call_args
    assert "current.json" in call_args[0][0]


def test_get_current_weather_with_today_date() -> None:
    """Test that today's date returns current weather."""
    today = datetime.now().strftime("%Y-%m-%d")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = _mock_current_response()

    with patch(
        "app.tools.ollama_tools.httpx.get", return_value=mock_response
    ) as mock_get:
        with patch("app.tools.ollama_tools.WEATHER_API_KEY", "test-key"):
            get_weather_by_city.invoke({"city": "London", "date": today})

    # Verify current.json endpoint was called
    call_args = mock_get.call_args
    assert "current.json" in call_args[0][0]


# =============================================================================
# Historical Weather Tests
# =============================================================================


def test_get_historical_weather_success() -> None:
    """Test fetching historical weather successfully."""
    past_date = "2024-06-15"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = _mock_history_response()

    with patch("app.tools.ollama_tools.httpx.get", return_value=mock_response):
        with patch("app.tools.ollama_tools.WEATHER_API_KEY", "test-key"):
            result = get_weather_by_city.invoke({"city": "London", "date": past_date})

    assert "Historical Weather in London" in result
    assert past_date in result
    assert "Max Temperature" in result


def test_get_historical_weather_uses_history_endpoint() -> None:
    """Test that past dates use the history.json endpoint."""
    past_date = "2024-01-15"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = _mock_history_response()

    with patch(
        "app.tools.ollama_tools.httpx.get", return_value=mock_response
    ) as mock_get:
        with patch("app.tools.ollama_tools.WEATHER_API_KEY", "test-key"):
            get_weather_by_city.invoke({"city": "London", "date": past_date})

    call_args = mock_get.call_args
    assert "history.json" in call_args[0][0]


def test_get_historical_weather_before_2010_error() -> None:
    """Test that dates before 2010 return an error."""
    with patch("app.tools.ollama_tools.WEATHER_API_KEY", "test-key"):
        result = get_weather_by_city.invoke({"city": "London", "date": "2009-12-31"})

    assert "Error" in result
    assert "2010-01-01" in result


# =============================================================================
# Forecast Weather Tests
# =============================================================================


def test_get_forecast_weather_success() -> None:
    """Test fetching forecast weather successfully."""
    future_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = _mock_forecast_response()

    with patch("app.tools.ollama_tools.httpx.get", return_value=mock_response):
        with patch("app.tools.ollama_tools.WEATHER_API_KEY", "test-key"):
            result = get_weather_by_city.invoke({"city": "London", "date": future_date})

    assert "Weather Forecast for London" in result
    assert "Chance of Rain" in result


def test_get_forecast_weather_uses_forecast_endpoint() -> None:
    """Test that future dates use the forecast.json endpoint."""
    future_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = _mock_forecast_response()

    with patch(
        "app.tools.ollama_tools.httpx.get", return_value=mock_response
    ) as mock_get:
        with patch("app.tools.ollama_tools.WEATHER_API_KEY", "test-key"):
            get_weather_by_city.invoke({"city": "London", "date": future_date})

    call_args = mock_get.call_args
    assert "forecast.json" in call_args[0][0]


def test_get_forecast_weather_beyond_14_days_error() -> None:
    """Test that dates more than 14 days ahead return an error."""
    future_date = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")

    with patch("app.tools.ollama_tools.WEATHER_API_KEY", "test-key"):
        result = get_weather_by_city.invoke({"city": "London", "date": future_date})

    assert "Error" in result
    assert "14 days" in result


# =============================================================================
# Error Handling Tests
# =============================================================================


def test_get_weather_no_api_key() -> None:
    """Test that missing API key returns an error."""
    with patch("app.tools.ollama_tools.WEATHER_API_KEY", ""):
        result = get_weather_by_city.invoke({"city": "London"})

    assert "Error" in result
    assert "API key" in result


def test_get_weather_invalid_date_format() -> None:
    """Test that invalid date format returns an error."""
    with patch("app.tools.ollama_tools.WEATHER_API_KEY", "test-key"):
        result = get_weather_by_city.invoke({"city": "London", "date": "15-06-2024"})

    assert "Error" in result
    assert "YYYY-MM-DD" in result


def test_get_weather_api_error() -> None:
    """Test handling of API errors."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.content = b'{"error": {"message": "City not found"}}'
    mock_response.json.return_value = {"error": {"message": "City not found"}}

    with patch("app.tools.ollama_tools.httpx.get", return_value=mock_response):
        with patch("app.tools.ollama_tools.WEATHER_API_KEY", "test-key"):
            result = get_weather_by_city.invoke({"city": "InvalidCity123"})

    assert "Error" in result


def test_get_weather_connection_error() -> None:
    """Test handling of connection errors."""
    import httpx

    with patch(
        "app.tools.ollama_tools.httpx.get",
        side_effect=httpx.RequestError("Connection failed"),
    ):
        with patch("app.tools.ollama_tools.WEATHER_API_KEY", "test-key"):
            result = get_weather_by_city.invoke({"city": "London"})

    assert "Error" in result
    assert "connect" in result.lower()


# =============================================================================
# Formatting Function Tests
# =============================================================================


def test_format_current_weather() -> None:
    """Test current weather formatting."""
    location = {"name": "Paris", "country": "France"}
    current = {
        "temp_c": 22.0,
        "temp_f": 71.6,
        "condition": {"text": "Sunny"},
        "humidity": 50,
        "wind_kph": 10.0,
        "wind_dir": "N",
        "feelslike_c": 23.0,
    }

    result = _format_current_weather(location, current)

    assert "Paris" in result
    assert "France" in result
    assert "22.0°C" in result
    assert "Sunny" in result
    assert "50%" in result


def test_format_historical_weather() -> None:
    """Test historical weather formatting."""
    location = {"name": "Berlin", "country": "Germany"}
    day_data = {
        "day": {
            "maxtemp_c": 25.0,
            "maxtemp_f": 77.0,
            "mintemp_c": 18.0,
            "mintemp_f": 64.4,
            "avgtemp_c": 21.5,
            "avgtemp_f": 70.7,
            "condition": {"text": "Clear"},
            "maxwind_kph": 12.0,
            "totalprecip_mm": 0.0,
            "avghumidity": 55,
        }
    }

    result = _format_historical_weather(location, day_data, "2024-06-15")

    assert "Historical Weather in Berlin" in result
    assert "2024-06-15" in result
    assert "Max Temperature: 25.0°C" in result
    assert "Min Temperature: 18.0°C" in result


def test_format_forecast_weather() -> None:
    """Test forecast weather formatting."""
    location = {"name": "Tokyo", "country": "Japan"}
    day_data = {
        "day": {
            "maxtemp_c": 30.0,
            "maxtemp_f": 86.0,
            "mintemp_c": 24.0,
            "mintemp_f": 75.2,
            "avgtemp_c": 27.0,
            "avgtemp_f": 80.6,
            "condition": {"text": "Hot"},
            "daily_chance_of_rain": 20,
            "daily_chance_of_snow": 0,
            "maxwind_kph": 8.0,
            "avghumidity": 70,
        }
    }

    result = _format_forecast_weather(location, day_data, "2024-12-30")

    assert "Weather Forecast for Tokyo" in result
    assert "2024-12-30" in result
    assert "Chance of Rain: 20%" in result
    assert "Chance of Snow: 0%" in result


# =============================================================================
# Integration Tests
# =============================================================================


def test_weather_tool_is_langchain_tool() -> None:
    """Test that get_weather_by_city is a proper LangChain tool."""
    assert hasattr(get_weather_by_city, "invoke")
    assert hasattr(get_weather_by_city, "name")
    assert get_weather_by_city.name == "get_weather_by_city"


def test_weather_tool_has_description() -> None:
    """Test that the tool has a proper description."""
    assert get_weather_by_city.description is not None
    assert "weather" in get_weather_by_city.description.lower()
    assert "city" in get_weather_by_city.description.lower()
