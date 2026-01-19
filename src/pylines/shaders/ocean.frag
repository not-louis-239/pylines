// Copyright 2025-2026 Louis Masarei-Boulton
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#version 120

varying vec2 v_tex_coord;
varying vec3 v_world_xz;

uniform sampler2D u_texture;
uniform sampler2D u_heightmap;

uniform float u_brightness;
uniform float u_sea_level;
uniform float u_world_size;
uniform float u_min_h;
uniform float u_max_h;

const float MIN_OPACITY = 0.1;
const float MAX_OPACITY = 0.99;
const float K = 0.01514;

void main() {
    // Base ocean color
    vec4 color = texture2D(u_texture, v_tex_coord);
    color.rgb *= u_brightness;

    // Calculate UV coordinates for the heightmap based on world position
    vec2 heightmap_uv = (v_world_xz.xz / u_world_size) * 0.5 + 0.5;

    // Sample the heightmap
    float terrain_height_raw = texture2D(u_heightmap, heightmap_uv).r;

    // Convert raw height (0-1) to world height
    float terrain_height = u_min_h + terrain_height_raw * (u_max_h - u_min_h);

    // Calculate water depth
    float water_depth = u_sea_level - terrain_height;

    if (water_depth < 0.0) {
        // This shouldn't happen if the ocean is rendered correctly, but as a safeguard
        water_depth = 0.0;
    }

    // Calculate opacity using the Beer-Lambert-style formula
    float factor = 1.0 - exp(-K * water_depth);
    factor = clamp(factor, 0.0, 1.0);

    color.a = mix(MIN_OPACITY, MAX_OPACITY, factor);

    gl_FragColor = color;
}
