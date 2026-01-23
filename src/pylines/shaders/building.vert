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

attribute vec3 position;
attribute vec3 color;
attribute vec3 normal;
attribute float in_emissive;

varying vec3 vert_color;
varying vec3 vert_normal;
varying float v_emissive;

void main() {
    gl_Position = gl_ModelViewProjectionMatrix * vec4(position, 1.0);
    vert_color = color;
    // Transform normal to eye space
    vert_normal = gl_NormalMatrix * normal;
    v_emissive = in_emissive;
}