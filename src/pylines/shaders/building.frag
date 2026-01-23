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

void main() {
    if (v_emissive > 0.5) {
        gl_FragColor = vec4(vert_color, 1.0);
        return;
    }

    vec3 light_direction = normalize(vec3(0.5, 1.0, 0.7));
    float diffuse = max(dot(normalize(vert_normal), light_direction), 0.0);
    vec3 ambient = vec3(0.4, 0.4, 0.4);
    vec3 final_color = (ambient + diffuse) * vert_color * u_brightness;
    gl_FragColor = vec4(final_color, 1.0);
}