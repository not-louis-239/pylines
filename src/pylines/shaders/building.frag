#version 120

varying vec3 vert_color;
varying vec3 vert_normal;

uniform float u_brightness;

void main() {
    vec3 light_direction = normalize(vec3(0.5, 1.0, 0.7));
    float diffuse = max(dot(normalize(vert_normal), light_direction), 0.0);
    vec3 ambient = vec3(0.4, 0.4, 0.4);
    vec3 final_color = (ambient + diffuse) * vert_color * u_brightness;
    gl_FragColor = vec4(final_color, 1.0);
}