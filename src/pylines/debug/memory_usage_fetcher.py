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


from __future__ import annotations

import sys


class MemoryUsageFetcher:
    def __init__(self) -> None:
        pass

    def _get_unix_rss_bytes(self) -> int:
        assert sys.platform != "win32", "This function should only be called on Unix machines"

        import resource

        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # macOS: ru_maxrss is bytes; Linux: kilobytes.
        if sys.platform == "darwin":
            return int(rss)
        return int(rss * 1024)

    def _get_windows_rss_bytes(self) -> int:
        assert sys.platform == "win32", "This function should only be called on Windows machines"

        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        psapi = ctypes.WinDLL("psapi")
        kernel32 = ctypes.WinDLL("kernel32")
        handle = kernel32.GetCurrentProcess()

        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            raise OSError("GetProcessMemoryInfo failed")

        return int(counters.WorkingSetSize)

    def fetch_memory_usage(self) -> int:
        """Return the amount of memory being used by the program, in bytes
        e.g. 100,000,000 for 100 MB of memory usage."""

        if sys.platform == "win32":
            return self._get_windows_rss_bytes()

        return self._get_unix_rss_bytes()
