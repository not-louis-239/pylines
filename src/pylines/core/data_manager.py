# Copyright 2025-2026 Louis Masarei-Boulton
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module for managing user data, e.g. unit settings."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, fields
from enum import Enum, auto
from pathlib import Path
from typing import Any, Mapping, Self, TypeAlias

from pylines.core.paths import DIRECTORIES
from pylines.core.constants import __version__

JSONValue: TypeAlias = (
    str | int | float | bool | None |
    list["JSONValue"] |
    dict[str, "JSONValue"]
)
JSONObject = dict[str, JSONValue]  # Reserved for top-level JSON files

class LoadStatus(Enum):
    SUCCESS = auto()
    NEW = auto()
    CORRUPT = auto()
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
    invert_y_axis: bool = False
    cloud_config_idx: int = 0
    show_briefing: bool = True
    version: str = __version__

    def to_json(self) -> JSONValue:
        return asdict(self)

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> ConfigObject:
        field_names = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in field_names}
        return cls(**filtered)

def save_data(obj: JSONConvertible, path: Path = DIRECTORIES.data / "save_data.json") -> str | None:
    """
    Return:
        None  -> success
        str   -> error msg
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temporary file to avoid corruption
        # if the program errors mid-write
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(obj.to_json(), f, indent=4, ensure_ascii=False)
        tmp.replace(path)

        return None
    except Exception as e:
        return str(e)

def load_data(path: Path) -> tuple[ConfigObject, LoadStatus, str | None]:
    """
    Return:
        ConfigObject
        LoadStatus
        str | None
            None  -> success
            str   -> error msg
    """

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data: JSONObject = json.load(f)

        config = ConfigObject.from_json(raw_data)
        return config, LoadStatus.SUCCESS, None

    except FileNotFoundError:
        return ConfigObject(), LoadStatus.NEW, None

    except json.JSONDecodeError:
        return ConfigObject(), LoadStatus.CORRUPT, None

    except Exception as e:
        return ConfigObject(), LoadStatus.ERROR, str(e)
