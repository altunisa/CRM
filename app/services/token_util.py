import httpx
from app.core.config import settings


async def get_token() -> str:
    """
    BKST token alır
    """
    url = settings.MINISTRY_TOKEN_URL

    payload = {
        "grant_type": "password",
        "username": settings.MINISTRY_USERNAME,
        "password": settings.MINISTRY_PASSWORD,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, data=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    token = data.get("access_token")

    if not token:
        raise RuntimeError("Token alınamadı (access_token yok)")

    return token