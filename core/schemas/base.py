from pydantic import BaseModel as PydanticBaseModel
from typing import Any, Dict, List, Optional, Union, Generic, TypeVar


class BaseModel(PydanticBaseModel):
    class Config:
        from_attributes = True
