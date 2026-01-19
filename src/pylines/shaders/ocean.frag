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
varying float v_sea_level;
varying float v_terrain_height;

uniform sampler2D u_texture;
uniform float u_brightness;

const float MIN_OPACITY = 0.1;
const float MAX_OPACITY = 0.99;
const float K = 0.01514;  // light reduction per metre

void main() {
    // Base ocean color
    vec4 color = texture2D(u_texture, v_tex_coord);
    color.rgb *= u_brightness;

    // Calculate water depth from interpolated values
    float water_depth = v_sea_level - v_terrain_height;

    if (water_depth < 0.0) {
        water_depth = 0.0;
    }

    // Optical depth for aesthetics
    float optical_depth = water_depth * 0.2;

    // Calculate opacity using the Beer-Lambert-style formula
    float factor = 1.0 - exp(-K * optical_depth);
    factor = clamp(factor, 0.0, 1.0);

    color.a = mix(MIN_OPACITY, MAX_OPACITY, factor);

    gl_FragColor = color;
}