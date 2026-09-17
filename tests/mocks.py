from unittest.mock import AsyncMock


# Define your dummy objects
class DummyRedis:
    async def get(self, *args, **kwargs):
        return None

    async def set(self, *args, **kwargs):
        return True

    async def setex(self, *args, **kwargs):
        return True

    async def delete(self, *args, **kwargs):
        return True
