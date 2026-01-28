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

varying vec2 v_tex_coord;  // image coords
varying float v_height;    // world altitude
varying vec2 v_world_xz;   // world coords
varying vec3 v_normal;
varying vec3 v_world_pos;

// Terrain textures
uniform sampler2D sand_texture;
uniform sampler2D low_grass_texture;
uniform sampler2D high_grass_texture;
uniform sampler2D treeline_rock_texture;
uniform sampler2D alpine_rock_texture;
uniform sampler2D snow_texture;

// Noise texture
uniform sampler2D noise_texture;

// Clip plane
uniform float sea_level;

// Altitude thresholds (metres)
const float low_grass_level     =  150.0;
const float high_grass_level    =  800.0;
const float treeline_rock_level = 2200.0;
const float alpine_rock_level   = 4000.0;
const float snow_level          = 5500.0;

// Blend width
const float blend_range = 20.0;  // metres

// Time-based brightness
uniform float u_brightness;
uniform vec3 u_sun_direction;
uniform float u_min_brightness;
uniform float u_max_brightness;
uniform float u_shade_multiplier;

void main() {
    // Sample all textures
    vec4 sand          = texture2D(sand_texture, v_tex_coord);
    vec4 low_grass     = texture2D(low_grass_texture, v_tex_coord);
    vec4 high_grass    = texture2D(high_grass_texture, v_tex_coord);
    vec4 treeline_rock = texture2D(treeline_rock_texture, v_tex_coord);
    vec4 alpine_rock   = texture2D(alpine_rock_texture, v_tex_coord);
    vec4 snow          = texture2D(snow_texture, v_tex_coord);

    // Get noise value
    float noise = texture2D(
        noise_texture,
        v_world_xz * 0.00005
    ).r;
    noise = noise * 2.0 - 1.0;  // map to [-1, 1]

    float tex_height = v_height * (1.0+(noise*0.2)) + 50*noise;  // multiplicative noise scales with altitude

    // Warped terrain boundaries after noise
    float warped_low_grass     = low_grass_level     + noise * 40.0;
    float warped_high_grass    = high_grass_level    + noise * 80.0;
    float warped_treeline_rock = treeline_rock_level + noise * 120.0;
    float warped_alpine_rock   = alpine_rock_level   + noise * 160.0;
    float warped_snow          = snow_level          + noise * 300.0;

    // Blend factors
    float b_low_grass     = smoothstep(warped_low_grass     - blend_range, warped_low_grass     + blend_range, tex_height);
    float b_high_grass    = smoothstep(warped_high_grass    - blend_range, warped_high_grass    + blend_range, tex_height);
    float b_treeline_rock = smoothstep(warped_treeline_rock - blend_range, warped_treeline_rock + blend_range, tex_height);
    float b_alpine_rock   = smoothstep(warped_alpine_rock   - blend_range, warped_alpine_rock   + blend_range, tex_height);
    float b_snow          = smoothstep(warped_snow          - blend_range, warped_snow          + blend_range, tex_height);

    // Sequential blending (bottom → top)
    vec4 color = sand;
    color = mix(color, low_grass,  b_low_grass);
    color = mix(color, high_grass, b_high_grass);
    color = mix(color, treeline_rock, b_treeline_rock);
    color = mix(color, alpine_rock, b_alpine_rock);
    color = mix(color, snow, b_snow);

    // Calculate diffuse light (direct sunlight)
    float diffuse_factor = max(dot(normalize(v_normal), normalize(u_sun_direction)), 0.0);

    // Base moonlight brightness is always present
    float total_brightness = u_min_brightness;

    // Calculate sun's current strength above moonlight
    float sun_strength_from_hour = max(0.0, u_brightness - u_min_brightness);

    // The sun's additional brightness:
    // It's strongest when facing the sun (diffuse_factor = 1).
    // When not directly facing the sun (diffuse_factor < 1), the effect is reduced,
    // and for fully shaded areas (diffuse_factor = 0), the effect is reduced by u_shade_multiplier.
    float sun_additional_brightness = sun_strength_from_hour * (diffuse_factor + (1.0 - diffuse_factor) * u_shade_multiplier);
    total_brightness += sun_additional_brightness;

    // Combine color with calculated total brightness
    color.rgb *= total_brightness;

    gl_FragColor = color;
}
