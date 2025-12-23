import httpx
from langchain.tools import tool

from app.config import WEATHER_API_KEY, WEATHER_API_BASE_URL
from app.utils.logger import logger


@tool
def get_current_weather_by_city(city: str) -> str:
    """Get current weather information for a specific city.

    Args:
        city: The name of the city to get weather for (e.g., "London", "New York")

    Returns:
        Current weather information including temperature, conditions, humidity, and wind.
    """
    logger.info("Fetching weather data for city: %s", city)

    if not WEATHER_API_KEY:
        logger.error("Weather API key not configured")
        return "Error: Weather API key not configured"

    url = f"{WEATHER_API_BASE_URL}/current.json"
    params = {"key": WEATHER_API_KEY, "q": city, "aqi": "no"}

    logger.debug("Making request to Weather API: %s", url)

    try:
        response = httpx.get(url, params=params)

        if response.status_code != 200:
            logger.warning(
                "Weather API returned non-200 status: %d for city: %s",
                response.status_code,
                city,
            )
            return f"Error: Could not fetch weather for {city}"

        data = response.json()
        location = data["location"]
        current = data["current"]

        logger.info(
            "Successfully fetched weather for %s, %s - Temp: %s°C",
            location["name"],
            location["country"],
            current["temp_c"],
        )

        return (
            f"Weather in {location['name']}, {location['country']}:\n\n"
            f"Temperature: {current['temp_c']}°C ({current['temp_f']}°F)\n"
            f"Condition: {current['condition']['text']}\n"
            f"Humidity: {current['humidity']}%\n"
            f"Wind: {current['wind_kph']} km/h {current['wind_dir']}\n"
            f"Feels like: {current['feelslike_c']}°C\n\n"
        )
    except httpx.RequestError as e:
        logger.error("HTTP request error while fetching weather for %s: %s", city, e)
        return f"Error: Could not connect to weather service for {city}"
    except (KeyError, TypeError) as e:
        logger.error("Error parsing weather response for %s: %s", city, e)
        return f"Error: Invalid response from weather service for {city}"
    