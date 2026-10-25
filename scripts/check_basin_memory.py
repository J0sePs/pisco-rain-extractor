"""Measure time and peak memory of a basin extraction at the size limit (ADR-0017).

Extracts a rectangle whose bounding box holds 50 × 50 = 2500 cells of the real daily file for
1981-2025 through the repository (time-blocked box reads, ADR-0005) and prints the elapsed time
and the peak working set of the process. Exits 1 when the peak reaches the limit. Usage:

    uv run python scripts/check_basin_memory.py [--limit-mb 300]
"""

import argparse
import ctypes
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shapely.geometry import box  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.repositories.pisco_repository import DatasetKind, PiscoRepository  # noqa: E402
from app.services.basin_geometry import BasinGeometry  # noqa: E402
from app.services.basin_service import MAX_BOX_CELLS, extract_basin  # noqa: E402

# Centers -76.95 .. -72.05 and -13.95 .. -9.05 (central Andes): 50 columns and 50 rows.
RECTANGLE = (-76.95, -13.95, -72.05, -9.05)


class _MemoryCounters(ctypes.Structure):
    _fields_ = [  # noqa: RUF012 (ctypes layout)
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def memory_mb() -> tuple[float, float]:
    """Current and peak resident memory of this process in MB."""
    if sys.platform == "win32":
        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.K32GetProcessMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_MemoryCounters),
            ctypes.c_ulong,
        ]
        counters = _MemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        process = kernel32.GetCurrentProcess()
        if not kernel32.K32GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb):
            raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo failed")
        return counters.WorkingSetSize / 2**20, counters.PeakWorkingSetSize / 2**20
    import resource

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mb = peak / 2**20 if sys.platform == "darwin" else peak / 2**10  # bytes vs KB
    return float("nan"), peak_mb


def main(argv: list[str] | None = None) -> int:
    """Print the measurement and return the exit code (0 when the peak is below the limit)."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit-mb", type=float, default=300.0)
    args = parser.parse_args(argv)

    repo = PiscoRepository.open(get_settings())
    try:
        calendar = repo.time_index(DatasetKind.DAILY)
        if calendar is None:
            print("Daily data is not available")
            return 1
        first, last = calendar[0].year, calendar[-1].year
        current, before_peak = memory_mb()
        grid_box = repo.grid_box(*RECTANGLE)
        print(f"Bounding box: {grid_box.lat.size} x {grid_box.lon.size} = {grid_box.size} cells")
        if grid_box.size != MAX_BOX_CELLS:
            print(f"Expected {MAX_BOX_CELLS} cells; check RECTANGLE")
            return 1
        print(f"Block length: {repo.time_block_length()} days; years {first}-{last}")
        print(f"Memory after opening the files: {current:.0f} MB (peak {before_peak:.0f} MB)")
        basin = BasinGeometry("check_basin_memory", 1, box(*RECTANGLE))
        start = time.perf_counter()
        result = extract_basin(repo, basin, first, last)
        elapsed = time.perf_counter() - start
    finally:
        repo.close()
    _, peak = memory_mb()
    print(f"Cells used {result.cells_used}, excluded {result.cells_excluded}")
    print(f"Days {result.total_days}, missing {result.missing_days}")
    print(f"Elapsed: {elapsed:.1f} s")
    print(f"Peak working set: {peak:.0f} MB (limit {args.limit_mb:.0f} MB)")
    return 0 if peak < args.limit_mb else 1


if __name__ == "__main__":
    sys.exit(main())
