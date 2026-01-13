#version 120

attribute vec3 position;
attribute vec2 tex_coord;

varying vec2 v_tex_coord;
varying float v_height;

void main() {
    v_tex_coord = tex_coord;
    v_height = position.y;
    gl_Position = gl_ModelViewProjectionMatrix * vec4(position, 1.0);
}
