import os
from typing import cast

SECRET_KEY = cast(str, os.getenv("REDIS_SECRET_KEY"))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "300"))
REDIS_URL = cast(str, os.getenv("REDIS_URL"))
