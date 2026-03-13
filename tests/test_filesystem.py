import os
import shutil
from pathlib import Path

import pytest

from tools import filesystem


def test_create_list_find_move(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    # create files
    (src / "alpha.txt").write_text("hello")
    (src / "beta.pdf").write_text("pdf")

    # create_folder
    out = filesystem.create_folder(str(dst))
    assert "Created" in out or "exists" in out

    # list_files
    listing = filesystem.list_files(str(src))
    assert "alpha.txt" in listing

    # find_files
    found = filesystem.find_files("alpha", str(src))
    assert "alpha.txt" in found

    # preview_move_matching (only .pdf)
    preview = filesystem.preview_move_matching("*", str(src), extensions=[".pdf"])
    assert "beta.pdf" in preview

    # move_matching
    moved = filesystem.move_matching("*", str(src), str(dst), extensions=[".pdf"]) 
    assert "beta.pdf" in moved
    assert (dst / "beta.pdf").exists()
