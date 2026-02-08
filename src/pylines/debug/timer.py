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

import time
from functools import wraps
from typing import Callable

START_TIME = time.perf_counter()
last_segment_time = START_TIME

MAX_ACCEPTABLE = 2.5  # ms

def rgb(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"

def lerp_colours(
        c1: tuple[int, int, int],
        c2: tuple[int, int, int],
        weight: float, /
    ) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, weight))
    r = int(c1[0] + t * (c2[0] - c1[0]))
    g = int(c1[1] + t * (c2[1] - c1[1]))
    b = int(c1[2] + t * (c2[2] - c1[2]))
    return (r, g, b)

def get_duration_colour(ms: float) -> str:
    """Returns an ANSI escape code based on the duration relative to MAX_ACCEPTABLE."""
    half_point = MAX_ACCEPTABLE / 2

    if ms <= half_point:
        # Interpolate Green -> Orange
        weight = ms / half_point
        c = lerp_colours(COL_ACCEPTABLE, COL_HALF_ACCEPTABLE, weight)
    else:
        # Interpolate Orange -> Red
        weight = (ms - half_point) / half_point
        c = lerp_colours(COL_HALF_ACCEPTABLE, COL_UNACCEPTABLE, weight)

    return rgb(*c)

COL_ACCEPTABLE = (110, 255, 110)
COL_HALF_ACCEPTABLE = (255, 255, 110)
COL_UNACCEPTABLE = (255, 110, 110)

COL_TOTAL = "\033[97m"

COL_NAMES_SEGMENTS = "\033[34m"
COL_NAMES_FUNCS = "\033[94m"
COL_RESET = "\033[0m"

def log_segment(seg_name: str | None = None):
    global last_segment_time
    now = time.perf_counter()
    duration_ms = (now - last_segment_time) * 1000

    if seg_name:
        colour = get_duration_colour(duration_ms)
        print(f"Segment {COL_NAMES_SEGMENTS}'{seg_name}'{COL_RESET} completed in: "
              f"{colour}{duration_ms:,.2f} ms{COL_RESET}")

    last_segment_time = now

def log_total_time():
    elapsed_time = time.perf_counter() - START_TIME
    print(f"Total time elapsed: {COL_TOTAL}{elapsed_time:,.4f}s{COL_RESET}")

def timer(func: Callable) -> Callable:
    @wraps(func)
    def timed_func(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000

        colour = get_duration_colour(duration_ms)
        print(f"Time taken for function {COL_NAMES_FUNCS}'{func.__name__}'{COL_RESET}: "
              f"{colour}{duration_ms:.2f} ms{COL_RESET}")
        return result
    return timed_func