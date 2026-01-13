#version 120

varying vec2 v_tex_coord;
varying float v_height;

// Terrain textures
uniform sampler2D sand_texture;
uniform sampler2D low_grass_texture;
uniform sampler2D high_grass_texture;
uniform sampler2D treeline_rock_texture;
uniform sampler2D alpine_rock_texture;
uniform sampler2D snow_texture;

// Altitude thresholds (metres)
const float low_grass_level     = 30.0;
const float high_grass_level    = 800.0;
const float treeline_rock_level = 2200.0;
const float alpine_rock_level   = 4000.0;
const float snow_level          = 5500.0;

// Blend width
const float blend_range = 50.0;

void main() {
    // Sample all textures
    vec4 sand          = texture2D(sand_texture, v_tex_coord);
    vec4 low_grass     = texture2D(low_grass_texture, v_tex_coord);
    vec4 high_grass    = texture2D(high_grass_texture, v_tex_coord);
    vec4 treeline_rock = texture2D(treeline_rock_texture, v_tex_coord);
    vec4 alpine_rock   = texture2D(alpine_rock_texture, v_tex_coord);
    vec4 snow          = texture2D(snow_texture, v_tex_coord);

    // Blend factors
    float b_low_grass     = smoothstep(low_grass_level     - blend_range, low_grass_level     + blend_range, v_height);
    float b_high_grass    = smoothstep(high_grass_level    - blend_range, high_grass_level    + blend_range, v_height);
    float b_treeline_rock = smoothstep(treeline_rock_level - blend_range, treeline_rock_level + blend_range, v_height);
    float b_alpine_rock   = smoothstep(alpine_rock_level   - blend_range, alpine_rock_level   + blend_range, v_height);
    float b_snow          = smoothstep(snow_level          - blend_range, snow_level          + blend_range, v_height);

    // Sequential blending (bottom → top)
    vec4 color = sand;
    color = mix(color, low_grass,  b_low_grass);
    color = mix(color, high_grass, b_high_grass);
    color = mix(color, treeline_rock, b_treeline_rock);
    color = mix(color, alpine_rock, b_alpine_rock);
    color = mix(color, snow, b_snow);

    gl_FragColor = color;
}
