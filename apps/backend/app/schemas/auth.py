import uuid

from pydantic import BaseModel


class DeviceAuthResponse(BaseModel):
    user_id: uuid.UUID
    api_token: str
