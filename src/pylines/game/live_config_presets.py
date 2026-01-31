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

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..objects.scenery.sky import CloudLayer

if TYPE_CHECKING:
    from ..core.asset_manager import ConfigPresets, Images

@dataclass
class CloudConfig:
    common_name: str
    layers: list[CloudLayer]

class LiveConfigPresets:
    """Runtime container for config presets"""

    def __init__(
            self,
            config_presets: ConfigPresets,
            images: Images
        ) -> None:
        # Cloud layers
        self.cloud_configs: list[CloudConfig] = [
            CloudConfig(
                cloud_config["common_name"],
                [
                    CloudLayer(
                        cloud_layer["altitude"],
                        cloud_layer["thickness"],
                        cloud_layer["coverage"],
                        cloud_layer["seed"],
                        images.cloud_blob
                    ) for cloud_layer in cloud_config["layers"]
                ]
            ) for cloud_config in config_presets.cloud_configs
        ]
