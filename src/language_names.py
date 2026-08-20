from pathlib import Path


LANGUAGE_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "python": (".py",),
    "javascript": (".js", ".jsx", ".mjs", ".cjs"),
    "typescript": (".ts",),
    "tsx": (".tsx",),
    "go": (".go",),
    "rust": (".rs",),
    "c": (".c", ".h"),
    "cpp": (".cpp", ".cc", ".cxx", ".hpp", ".hh"),
}


def language_for_extension(path: str) -> str | None:
    ext = Path(path).suffix
    for name, extensions in LANGUAGE_EXTENSIONS.items():
        if ext in extensions:
            return name
    return None
