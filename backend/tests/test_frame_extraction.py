import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path

from services.detectors.frame_extraction import ExtractedFrame, prepare_frames


def _make_frames(tmp_path: Path, count: int) -> list[Path]:
    paths = []
    for i in range(count):
        p = tmp_path / f"frame_{i:03d}.jpg"
        p.write_bytes(b"\xff\xd8\xff")  # minimal jpeg-ish header
        paths.append(p)
    return paths


def test_prepare_frames_indexes_existing_files(tmp_path):
    paths = _make_frames(tmp_path, 3)
    frames = prepare_frames(paths)
    assert [f.index for f in frames] == [0, 1, 2]
    assert all(isinstance(f, ExtractedFrame) for f in frames)
    assert [f.path for f in frames] == paths

def test_prepare_frames_skips_missing_and_reindexes(tmp_path):
    paths = _make_frames(tmp_path, 2)
    mixed = [paths[0], tmp_path / "missing.jpg", paths[1]]
    frames = prepare_frames(mixed)
    assert [f.index for f in frames] == [0, 1]  # contiguous, missing dropped
    assert [f.path for f in frames] == [paths[0], paths[1]]

def test_prepare_frames_empty_input():
    assert prepare_frames([]) == []

def test_prepare_frames_all_missing(tmp_path):
    assert prepare_frames([tmp_path / "a.jpg", tmp_path / "b.jpg"]) == []

def test_prepare_frames_accepts_str_paths(tmp_path):
    paths = _make_frames(tmp_path, 1)
    frames = prepare_frames([str(paths[0])])
    assert len(frames) == 1
    assert frames[0].path == paths[0]
