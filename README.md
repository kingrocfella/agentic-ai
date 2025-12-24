# AI Agent API

A FastAPI-based AI agent service with JWT authentication, Redis storage, and LLM-powered weather queries using Ollama and LangGraph.

## Features

- **Authentication**: JWT-based auth with register, login, and logout endpoints
- **AI Agent**: LangGraph-powered ReAct agent with tool calling capabilities
- **Weather Tool**: Get current, historical, and forecast weather data via WeatherAPI.com
- **Streaming**: Server-Sent Events (SSE) for real-time agent responses
- **Logging**: Comprehensive logging with rotating file handlers

## Tech Stack

| Component   | Technology        |
| ----------- | ----------------- |
| Framework   | FastAPI           |
| LLM         | Ollama (llama3.2) |
| Agent       | LangGraph ReAct   |
| Database    | Redis             |
| Auth        | JWT (python-jose) |
| Weather API | WeatherAPI.com    |

## Project Structure

```
ai-agent/
├── app/
│   ├── agents/           # LangGraph agent implementation
│   ├── middleware/       # Auth & logging middleware
│   ├── routes/           # API endpoints
│   ├── schemas/          # Pydantic models
│   ├── tools/            # LangChain tools (weather)
│   ├── utils/            # Logger, SSE utilities
│   ├── config.py         # Configuration
│   ├── database.py       # Redis client
│   └── main.py           # FastAPI app
├── tests/                # Unit tests
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- WeatherAPI.com API key (free tier available)

### 1. Clone and Configure

```bash
git clone https://github.com/kingrocfella/agentic-ai
cd agentic-ai
```

Create a `.env` file:

```env
REDIS_SECRET_KEY=your-secret-key-here
REDIS_URL=redis://redis:6379/0
ACCESS_TOKEN_EXPIRE_MINUTES=30
WEATHER_API_KEY=your-weatherapi-key
WEATHER_API_BASE_URL=https://api.weatherapi.com/v1
OLLAMA_HOST=http://ollama:11434
```

### 2. Start Services

```bash
docker-compose up --build
```

This starts:

- **API** on `http://localhost:8000`
- **Redis** on `localhost:6379`
- **Ollama** on `localhost:11434` (auto-pulls llama3.2)

### 3. Verify

```bash
curl http://localhost:8000/health
```

## Weather Tool

The `get_weather_by_city` tool supports:

| Type       | Date Parameter    | API Used         |
| ---------- | ----------------- | ---------------- |
| Current    | None or today     | `/current.json`  |
| Historical | Past date (≥2010) | `/history.json`  |
| Forecast   | Future (≤14 days) | `/forecast.json` |

**Examples:**

- "What's the weather in London?" → Current weather
- "What was the weather in Paris on June 15, 2024?" → Historical
- "What will the weather be in Tokyo next week?" → Forecast

## Development

### Local Setup (Python 3.11+)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run Tests

```bash
pytest tests/ -v --cov=app
```

### API Documentation

Once running, access:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
