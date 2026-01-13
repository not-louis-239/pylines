#version 120

// Varying variables are used to pass data from the vertex shader
// to the fragment shader.
varying vec2 v_tex_coord;
varying float v_height;

void main() {
    // Pass the original texture coordinate to the fragment shader.
    // gl_MultiTexCoord0 is a built-in that gets the first texture coordinate.
    v_tex_coord = gl_MultiTexCoord0.xy;

    // Pass the world-space height of the vertex.
    v_height = gl_Vertex.y;

    // Apply the standard model-view-projection matrix to transform the vertex.
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
}
