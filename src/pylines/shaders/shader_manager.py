import OpenGL.GL as gl
from typing import cast

def load_shader_script(vert_path: str, frag_path: str) -> int:
    with open(vert_path, "r", encoding="utf-8") as f:
        vert_source = f.read()

    with open(frag_path, "r", encoding="utf-8") as f:
        frag_source = f.read()

    vert_shader = gl.glCreateShader(gl.GL_VERTEX_SHADER)
    frag_shader = gl.glCreateShader(gl.GL_FRAGMENT_SHADER)

    gl.glShaderSource(vert_shader, vert_source)
    gl.glShaderSource(frag_shader, frag_source)

    gl.glCompileShader(vert_shader)
    if not gl.glGetShaderiv(vert_shader, gl.GL_COMPILE_STATUS):
        raise RuntimeError(gl.glGetShaderInfoLog(vert_shader).decode())

    gl.glCompileShader(frag_shader)
    if not gl.glGetShaderiv(frag_shader, gl.GL_COMPILE_STATUS):
        raise RuntimeError(gl.glGetShaderInfoLog(frag_shader).decode())

    program = cast(int, gl.glCreateProgram())

    gl.glAttachShader(program, vert_shader)
    gl.glAttachShader(program, frag_shader)
    gl.glLinkProgram(program)

    if not gl.glGetProgramiv(program, gl.GL_LINK_STATUS):
        raise RuntimeError(gl.glGetProgramInfoLog(program).decode())

    gl.glDeleteShader(vert_shader)
    gl.glDeleteShader(frag_shader)

    return program
