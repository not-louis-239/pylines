"""Module for managing user data, e.g. unit settings."""

from __future__ import annotations
import json
import copy
from typing import Self, TypeAlias, Literal, Mapping, Any
from dataclasses import dataclass, asdict, fields
from abc import ABC, abstractmethod
from enum import Enum, auto

JSONValue: TypeAlias = (
    str | int | float | bool | None |
    list["JSONValue"] |
    dict[str, "JSONValue"]
)
JSONObject = dict[str, JSONValue]  # Reserved for top-level JSON files

class LoadStatus(Enum):
    SUCCESS = auto()
    NEW = auto()
    CORRUPTED = auto()
    ERROR = auto()

class JSONConvertible(ABC):
    """
    Base class for items that are convertible to and from JSON.
    Use this for objects that should persist between sessions, e.g. settings.
    """

    @abstractmethod
    def to_json(self) -> JSONValue:
        """Serialise to dict"""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def from_json(cls, data: JSONValue) -> Self:
        """Create from dict"""
        raise NotImplementedError

@dataclass
class ConfigObject(JSONConvertible):
    time: Literal["system", "custom"] = "system"  # "system" or "custom"
    time_custom: int = 18
    time_zone: int = 0  # GMT offset in hours

    def to_json(self) -> JSONValue:
        return asdict(self)

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> ConfigObject:
        field_names = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in field_names}
        return cls(**filtered)

def save_data(obj: JSONConvertible, filename="save_data.json") -> str | None:
    """
    Return:
        None  -> success
        str   -> error msg
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            raw_data: JSONValue = obj.to_json()
            json.dump(raw_data, f, indent=4, ensure_ascii=False)
        return None
    except Exception as e:
        return str(e)

def load_data(filename="save_data.json") -> tuple[ConfigObject, LoadStatus, str | None]:
    """
    Return:
        ConfigObject
        LoadStatus
        str | None
            None  -> success
            str   -> error msg
    """

    try:
        with open(filename, "r", encoding="utf-8") as f:
            raw_data: JSONObject = json.load(f)

        config = ConfigObject.from_json(raw_data)
        return config, LoadStatus.SUCCESS, None

    except FileNotFoundError:
        return ConfigObject(), LoadStatus.NEW, None

    except json.JSONDecodeError:
        return ConfigObject(), LoadStatus.CORRUPTED, None

    except Exception as e:
        return ConfigObject(), LoadStatus.ERROR, str(e)
