// Copyright 2025-2026 Louis Masarei-Boulton

// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at

//     http://www.apache.org/licenses/LICENSE-2.0

// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#version 120

varying vec3 vert_color;
varying vec3 vert_normal;
varying float v_emissive;

uniform float u_brightness;
uniform vec3 u_sun_direction;
uniform float u_min_brightness;
uniform float u_max_brightness;
uniform float u_shade_multiplier;

void main() {
    if (v_emissive > 0.5) {
        gl_FragColor = vec4(vert_color, 1.0);
        return;
    }

    // Calculate diffuse light (direct sunlight)
    float diffuse_factor = max(dot(normalize(vert_normal), normalize(u_sun_direction)), 0.0);

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

    vec3 final_color = vert_color * total_brightness;
    gl_FragColor = vec4(final_color, 1.0);
}