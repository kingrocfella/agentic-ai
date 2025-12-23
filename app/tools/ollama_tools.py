import httpx
from langchain.tools import tool

from app.config import WEATHER_API_KEY, WEATHER_API_BASE_URL


@tool
def get_current_weather_by_city(city: str) -> str:
    """Get current weather information for a specific city.
    
    Args:
        city: The name of the city to get weather for (e.g., "London", "New York")
    
    Returns:
        Current weather information including temperature, conditions, humidity, and wind.
    """
    if not WEATHER_API_KEY:
        return "Error: Weather API key not configured"

    url = f"{WEATHER_API_BASE_URL}/current.json"

    params = {"key": WEATHER_API_KEY, "q": city, "aqi": "no"}

    response = httpx.get(url, params=params)

    if response.status_code != 200:
        return f"Error: Could not fetch weather for {city}"

    data = response.json()
    location = data["location"]
    current = data["current"]

    return (
        f"Weather in {location['name']}, {location['country']}:\n"
        f"Temperature: {current['temp_c']}°C ({current['temp_f']}°F)\n"
        f"Condition: {current['condition']['text']}\n"
        f"Humidity: {current['humidity']}%\n"
        f"Wind: {current['wind_kph']} km/h {current['wind_dir']}\n"
        f"Feels like: {current['feelslike_c']}°C"
    )
