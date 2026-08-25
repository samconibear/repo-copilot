from .models import ChunkConfig

CHUNK_CONFIGS: dict[str, ChunkConfig] = {
    "default": ChunkConfig(
        split_threshold=4000,
        window_size=2000,
        window_overlap=400,
        gap_min_size=40,
    ),
      "small": ChunkConfig(
        split_threshold=1000,
        window_size=800,
        window_overlap=200,
        gap_min_size=10,
    ),
}
