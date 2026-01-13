#version 120

varying vec2 v_tex_coord;
varying float v_height;

void main() {
    v_tex_coord = gl_MultiTexCoord0.xy;
    v_height = gl_Vertex.y;
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
}
