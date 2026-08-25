from src.rag.filtering import language_for_file
from src.rag.loaders.models import SourceFile


def test_known_extension_maps_to_language():
    f = SourceFile(path="a.py", data=b"x = 1\n")
    assert language_for_file(f) == "python"


def test_unknown_extension_falls_back_to_text():
    f = SourceFile(path="README.md", data=b"hello\n")
    assert language_for_file(f) == "text"


def test_excluded_dir_is_skipped():
    f = SourceFile(path="node_modules/pkg/index.js", data=b"x\n")
    assert language_for_file(f) is None


def test_oversized_file_is_skipped():
    f = SourceFile(path="big.py", data=b"x" * 500_001)
    assert language_for_file(f) is None


def test_binary_sniff_skips_null_byte_in_first_8kb():
    f = SourceFile(path="a.py", data=b"\x00" + b"x" * 100)
    assert language_for_file(f) is None

