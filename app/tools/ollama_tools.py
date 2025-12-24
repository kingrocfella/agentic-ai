from datetime import datetime

import httpx
from langchain.tools import tool

from app.config import WEATHER_API_KEY, WEATHER_API_BASE_URL
from app.utils.logger import logger


@tool
def get_weather_by_city(city: str, date: str | None = None) -> str:
    """Get weather information for a specific city. Supports current, historical, and forecast weather.

    Args:
        city: The name of the city to get weather for (e.g., "London", "New York")
        date: Optional date in YYYY-MM-DD format. If not provided, returns current weather.
              For past dates (after 2010-01-01): returns historical weather.
              For future dates (up to 14 days ahead): returns forecast weather.

    Returns:
        Weather information including temperature, conditions, humidity, and wind.
    """
    logger.info("Fetching weather data for city: %s, date: %s", city, date or "current")

    if not WEATHER_API_KEY:
        logger.error("Weather API key not configured")
        return "Error: Weather API key not configured"

    today = datetime.now().date()

    # Determine which API to use based on date
    if date is None:
        # Current weather
        endpoint = "current.json"
        params: dict[str, str | int] = {"key": WEATHER_API_KEY, "q": city, "aqi": "no"}
        weather_type = "current"
        logger.info("Fetching current weather for city: %s", city)
    else:
        logger.info("Fetching weather for city: %s on date: %s", city, date)
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Invalid date format: %s", date)
            return f"Error: Invalid date format '{date}'. Please use YYYY-MM-DD format."

        days_diff = (target_date - today).days

        if days_diff < 0:
            # Historical weather
            min_date = datetime(2010, 1, 1).date()
            if target_date < min_date:
                logger.error("Historical data only available from 2010-01-01 onwards.")
                return "Error: Historical data only available from 2010-01-01 onwards."
            endpoint = "history.json"
            params = {"key": WEATHER_API_KEY, "q": city, "dt": date}
            weather_type = "historical"
            logger.info(
                "Fetching historical weather for city: %s on date: %s", city, date
            )
        elif days_diff == 0:
            # Today - use current weather
            endpoint = "current.json"
            params = {"key": WEATHER_API_KEY, "q": city, "aqi": "no"}
            weather_type = "current"
            logger.info("Fetching current weather for city: %s", city)
        elif days_diff <= 14:
            # Forecast weather (up to 14 days)
            endpoint = "forecast.json"
            params = {"key": WEATHER_API_KEY, "q": city, "dt": date, "days": 1}
            weather_type = "forecast"
            logger.info(
                "Fetching forecast weather for city: %s on date: %s", city, date
            )
        else:
            logger.error(
                "Forecast only available up to 14 days ahead. Requested: %d days.",
                days_diff,
            )
            return f"Error: Forecast only available up to 14 days ahead. Requested: {days_diff} days."

    url = f"{WEATHER_API_BASE_URL}/{endpoint}"
    logger.debug(
        "Making request to Weather API: %s with params: %s",
        url,
        {k: v for k, v in params.items() if k != "key"},
    )

    try:
        response = httpx.get(url, params=params)

        if response.status_code != 200:
            logger.warning(
                "Weather API returned non-200 status: %d for city: %s",
                response.status_code,
                city,
            )
            error_data = response.json() if response.content else {}
            error_msg = error_data.get("error", {}).get("message", "Unknown error")
            logger.error("Could not fetch weather for %s: %s", city, error_msg)
            return f"Error: Could not fetch weather for {city}. {error_msg}"

        data = response.json()
        location = data["location"]

        if weather_type == "current":
            return _format_current_weather(location, data["current"])
        elif weather_type == "historical":
            assert date is not None
            return _format_historical_weather(
                location, data["forecast"]["forecastday"][0], date
            )
        else:  # forecast
            assert date is not None
            return _format_forecast_weather(
                location, data["forecast"]["forecastday"][0], date
            )

    except httpx.RequestError as e:
        logger.error("HTTP request error while fetching weather for %s: %s", city, e)
        return f"Error: Could not connect to weather service for {city}"
    except (KeyError, TypeError, IndexError) as e:
        logger.error("Error parsing weather response for %s: %s", city, e)
        return f"Error: Invalid response from weather service for {city}"


def _format_current_weather(location: dict, current: dict) -> str:
    """Format current weather data."""
    logger.info(
        "Successfully fetched current weather for %s, %s - Temp: %s°C",
        location["name"],
        location["country"],
        current["temp_c"],
    )

    return (
        f"Current Weather in {location['name']}, {location['country']}:\n\n"
        f"Temperature: {current['temp_c']}°C ({current['temp_f']}°F)\n"
        f"Condition: {current['condition']['text']}\n"
        f"Humidity: {current['humidity']}%\n"
        f"Wind: {current['wind_kph']} km/h {current['wind_dir']}\n"
        f"Feels like: {current['feelslike_c']}°C\n"
    )


def _format_historical_weather(location: dict, day_data: dict, date: str) -> str:
    """Format historical weather data."""
    day = day_data["day"]

    logger.info(
        "Successfully fetched historical weather for %s, %s on %s",
        location["name"],
        location["country"],
        date,
    )

    return (
        f"Historical Weather in {location['name']}, {location['country']} on {date}:\n\n"
        f"Max Temperature: {day['maxtemp_c']}°C ({day['maxtemp_f']}°F)\n"
        f"Min Temperature: {day['mintemp_c']}°C ({day['mintemp_f']}°F)\n"
        f"Average Temperature: {day['avgtemp_c']}°C ({day['avgtemp_f']}°F)\n"
        f"Condition: {day['condition']['text']}\n"
        f"Max Wind: {day['maxwind_kph']} km/h\n"
        f"Total Precipitation: {day['totalprecip_mm']} mm\n"
        f"Average Humidity: {day['avghumidity']}%\n"
    )


def _format_forecast_weather(location: dict, day_data: dict, date: str) -> str:
    """Format forecast weather data."""
    day = day_data["day"]

    logger.info(
        "Successfully fetched forecast for %s, %s on %s",
        location["name"],
        location["country"],
        date,
    )

    return (
        f"Weather Forecast for {location['name']}, {location['country']} on {date}:\n\n"
        f"Max Temperature: {day['maxtemp_c']}°C ({day['maxtemp_f']}°F)\n"
        f"Min Temperature: {day['mintemp_c']}°C ({day['mintemp_f']}°F)\n"
        f"Average Temperature: {day['avgtemp_c']}°C ({day['avgtemp_f']}°F)\n"
        f"Condition: {day['condition']['text']}\n"
        f"Chance of Rain: {day.get('daily_chance_of_rain', 'N/A')}%\n"
        f"Chance of Snow: {day.get('daily_chance_of_snow', 'N/A')}%\n"
        f"Max Wind: {day['maxwind_kph']} km/h\n"
        f"Average Humidity: {day['avghumidity']}%\n"
    )
