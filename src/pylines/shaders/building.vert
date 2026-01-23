#version 120

attribute vec3 position;
attribute vec3 color;
attribute vec3 normal;

varying vec3 vert_color;
varying vec3 vert_normal;

void main() {
    gl_Position = gl_ModelViewProjectionMatrix * vec4(position, 1.0);
    vert_color = color;
    // Transform normal to eye space
    vert_normal = gl_NormalMatrix * normal;
}