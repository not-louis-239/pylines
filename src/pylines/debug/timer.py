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
from typing import Callable
from functools import wraps

START_TIME = time.perf_counter()
last_segment_time = START_TIME

COL_EMPHASIS = "\033[32m"        # Green
COL_NAMES_SEGMENTS = "\033[31m"  # Red
COL_NAMES_FUNCS = "\033[34m"     # Blue
COL_RESET = "\033[0m"

def log_segment(seg_name: str | None = None):
    """Log segment duration and start a new segment. With no
    argument it just resets the segment timer silently."""
    global last_segment_time

    now = time.perf_counter()
    segment_duration = now - last_segment_time

    if seg_name is not None:
        if not seg_name:
            # Detect empty string as misuse
            raise ValueError("Segment name cannot be empty.")

        print(f"Segment {COL_NAMES_SEGMENTS}'{seg_name}'{COL_RESET} completed in: {COL_EMPHASIS}{segment_duration * 1000:,.2f} ms{COL_RESET}")

    # Start a new segment
    last_segment_time = now

def log_total_time():
    """Print the total time elapsed without resetting it"""
    elapsed_time = time.perf_counter() - START_TIME

    print(f"Total time elapsed: {COL_EMPHASIS}{elapsed_time:,.4f}s{COL_RESET}")

def timer(func: Callable) -> Callable:
    @wraps(func)
    def timed_func(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        time_taken = time.perf_counter() - start

        print(f"Time taken for function {COL_NAMES_FUNCS}'{func.__name__}'{COL_RESET}: {COL_EMPHASIS}{time_taken * 1000:.2f} ms{COL_RESET}")
        return result

    return timed_func