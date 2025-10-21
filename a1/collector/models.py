from pydantic import (
    BaseModel,
    Field,
    field_validator,
    UUID4,
)
from typing import Optional, Annotated
from datetime import datetime
import base64


class Frame(BaseModel):
    timestamp: datetime = Field(..., description="ISO 8601 timestamp of the frame")
    section: Annotated[
        int, Field(ge=1, description="Section number, must be non-negative")
    ]
    event: Annotated[
        str, Field(min_length=1, description="Event type, e.g., entry or exit")
    ]
    image: Annotated[
        str, Field(min_length=1, description="Base64-encoded image string")
    ]
    frame_uuid: UUID4 = Field(..., description="Unique UUID of the frame")
    extra_info: Optional[str] = Field(
        "", alias="extra-info", description="Optional extra information"
    )

    # model_config = {
    #     "populate_by_name": True  # allows using 'extra_info' when alias is 'extra-info'
    # }

    # Field-level validator: ensure image is valid base64
    @field_validator("image")
    def validate_base64(cls, v: str) -> str:
        try:
            base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError("image must be a valid base64 string")
        return v
