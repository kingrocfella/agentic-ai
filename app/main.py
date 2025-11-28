from fastapi import FastAPI

from app.routes import auth_router, health_router, agents_router

app = FastAPI(title="AI Agent API")

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(agents_router)
