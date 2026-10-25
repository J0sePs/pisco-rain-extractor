from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.config import Settings
from app.repositories.pisco_repository import (
    UNCHUNKED_BLOCK_DAYS,
    CellRef,
    PiscoRepository,
    lon_slice,
)
from tests.conftest import BASIN_CHUNKS, write_reference_dir
from tests.test_point_result_pages import precipitation_reads  # noqa: F401 (fixture)

START, END = date(1981, 1, 1), date(1985, 12, 31)


@pytest.fixture
def open_repo() -> Iterator[Callable[[Path], PiscoRepository]]:
    repos: list[PiscoRepository] = []

    def factory(directory: Path) -> PiscoRepository:
        repo = PiscoRepository.open(Settings(data_dir=directory))
        repos.append(repo)
        return repo

    yield factory
    for repo in repos:
        repo.close()


@pytest.fixture(scope="module")
def ascending_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return write_reference_dir(tmp_path_factory.mktemp("ascending"), ascending_lat=True)


@pytest.mark.parametrize("fixture", ["reference_dir", "reference_dir_float64", "ascending_dir"])
def test_box_selects_centers_within_bounds(
    fixture: str, request: pytest.FixtureRequest, open_repo: Callable[[Path], PiscoRepository]
) -> None:
    repo = open_repo(request.getfixturevalue(fixture))
    box = repo.grid_box(-76.30, -12.40, -76.10, -12.20)
    assert sorted(box.lat.tolist()) == [-12.35, -12.25]
    assert box.lon.tolist() == [-76.25, -76.15]
    assert box.size == 4


def test_bounds_on_centers_are_inclusive(
    reference_dir: Path, open_repo: Callable[[Path], PiscoRepository]
) -> None:
    box = open_repo(reference_dir).grid_box(-76.25, -12.35, -76.05, -12.15)
    assert box.lat.tolist() == [-12.15, -12.25, -12.35]  # file order (descending)
    assert box.lon.tolist() == [-76.25, -76.15, -76.05]


def test_box_outside_is_empty(
    reference_dir: Path, open_repo: Callable[[Path], PiscoRepository]
) -> None:
    box = open_repo(reference_dir).grid_box(-70.5, -10.5, -70.0, -10.0)
    assert box.size == 0


def test_cell_box_holds_one_cell(
    reference_dir: Path, open_repo: Callable[[Path], PiscoRepository]
) -> None:
    repo = open_repo(reference_dir)
    box = repo.cell_box(CellRef(lat_index=2, lon_index=2, lon=-76.15, lat=-12.25))
    assert box.lat.tolist() == [-12.25]
    assert box.lon.tolist() == [-76.15]


def test_lon_slice_rejects_descending_axis() -> None:
    with pytest.raises(ValueError, match="ascending"):
        lon_slice(np.array([-76.05, -76.15, -76.25]), -76.2, -76.1)


def test_block_length(
    basin_dir: Path, chunked_dir: Path, open_repo: Callable[[Path], PiscoRepository]
) -> None:
    assert open_repo(basin_dir).time_block_length() == UNCHUNKED_BLOCK_DAYS
    assert open_repo(chunked_dir).time_block_length() == BASIN_CHUNKS[0]


def test_blocks_match_single_cell_reads(
    chunked_dir: Path, open_repo: Callable[[Path], PiscoRepository]
) -> None:
    repo = open_repo(chunked_dir)
    box = repo.grid_box(-76.30, -12.40, -76.10, -12.20)
    blocks = list(repo.iter_box_blocks(box, START, END))
    dates = pd.DatetimeIndex(np.concatenate([d.to_numpy() for d, _ in blocks]))
    values = np.concatenate([v for _, v in blocks])
    assert values.dtype == np.float32
    assert values.shape == (1826, 2, 2)
    assert dates[0] == pd.Timestamp(START) and dates[-1] == pd.Timestamp(END)
    for i, lat in enumerate(box.lat):
        for j, lon in enumerate(box.lon):
            cell = repo.nearest_cell(float(lon), float(lat))
            expected = repo.read_cell_series(cell, START, END).to_numpy()
            np.testing.assert_array_equal(values[:, i, j], expected)


def test_blocks_align_with_chunks(
    chunked_dir: Path, open_repo: Callable[[Path], PiscoRepository]
) -> None:
    repo = open_repo(chunked_dir)
    box = repo.grid_box(-76.30, -12.40, -76.10, -12.20)
    blocks = list(repo.iter_box_blocks(box, date(1981, 2, 1), date(1981, 12, 31)))
    lengths = [len(d) for d, _ in blocks]
    assert lengths == [69, 100, 100, 65]  # positions 31..99, 100..199, 200..299, 300..364


def test_reads_cover_only_box_and_period(
    chunked_dir: Path,
    open_repo: Callable[[Path], PiscoRepository],
    precipitation_reads: list[tuple[int, ...]],  # noqa: F811
) -> None:
    repo = open_repo(chunked_dir)
    box = repo.grid_box(-76.30, -12.40, -76.10, -12.20)
    for _ in repo.iter_box_blocks(box, START, END):
        pass
    assert precipitation_reads
    assert all(shape[1] <= 2 and shape[2] <= 2 for shape in precipitation_reads)
    assert sum(shape[0] for shape in precipitation_reads) == 1826
