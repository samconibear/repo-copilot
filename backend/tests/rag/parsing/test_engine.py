from src.rag.parsing.engine import parse_file


def test_unknown_language_returns_no_symbols():
    assert parse_file("a.xyz", "cobol", b"anything") == []


def test_top_level_function():
    source = b"def foo(a, b):\n    return a + b\n"
    [sym] = parse_file("a.py", "python", source)
    assert sym.kind == "function"
    assert sym.name == "foo"
    assert sym.qualified_name == "foo"
    assert sym.parent is None
    assert sym.signature == "def foo(a, b):"
    assert sym.start_line == 1
    assert sym.end_line == 2


def test_method_gets_class_as_parent_and_upgraded_kind():
    source = b"class Point:\n    def dist(self):\n        return 0\n"
    symbols = parse_file("a.py", "python", source)
    kinds = {s.name: s for s in symbols}
    assert kinds["Point"].kind == "class"
    assert kinds["dist"].kind == "method"
    assert kinds["dist"].parent == "Point"
    assert kinds["dist"].qualified_name == "Point.dist"


def test_go_method_uses_receiver_owner_not_containers():
    source = b"package main\n\nfunc (p *Point) Dist() int {\n\treturn 0\n}\n"
    [sym] = parse_file("a.go", "go", source)
    assert sym.kind == "method"
    assert sym.parent == "Point"
    assert sym.qualified_name == "Point.Dist"


def test_malformed_source_does_not_raise():
    parse_file("a.py", "python", b"def foo(:::\n  not valid python at all")
