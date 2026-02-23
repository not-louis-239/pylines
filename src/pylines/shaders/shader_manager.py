# Copyright 2025-2026 Louis Masarei-Boulton
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path
from typing import Literal, cast

import OpenGL.GL as gl


class ShaderError(RuntimeError):
    def __init__(
            self, message: str,
            shader_type: Literal['vertex', 'fragment', 'program', None] = None,
            path: Path | None = None, log: str | None = None
        ) -> None:
        super().__init__(message)
        self.shader_type = shader_type  # "vertex", "fragment", or "program"
        self.path = path                # path to the shader file
        self.log = log                  # compiler/linker output

    def __str__(self) -> str:
        return (
            f"{self.args[0]}\n"
            f"Shader Type: {self.shader_type}\n"
            f"Path: {self.path}\n"
            f"Log: \n{self.log}"
        )

def load_shader_script(vert_path: Path, frag_path: Path) -> int:
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
        log = gl.glGetShaderInfoLog(vert_shader).decode()
        raise ShaderError(
            f"Error compiling vertex shader '{vert_path}'",
            shader_type="vertex",
            path=vert_path,
            log=log
        )

    gl.glCompileShader(frag_shader)
    if not gl.glGetShaderiv(frag_shader, gl.GL_COMPILE_STATUS):
        log = gl.glGetShaderInfoLog(frag_shader).decode()
        raise ShaderError(
            f"Error compiling fragment shader '{frag_path}'",
            shader_type="fragment",
            path=frag_path,
            log=log
        )

    program = cast(int, gl.glCreateProgram())

    gl.glAttachShader(program, vert_shader)
    gl.glAttachShader(program, frag_shader)
    gl.glLinkProgram(program)

    if not gl.glGetProgramiv(program, gl.GL_LINK_STATUS):
        log = gl.glGetProgramInfoLog(program).decode()
        raise ShaderError(
            "Shader program link failed",
            shader_type="program",
            log=log
        )

    gl.glDeleteShader(vert_shader)
    gl.glDeleteShader(frag_shader)

    return program
