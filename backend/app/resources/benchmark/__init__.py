"""Shipped benchmark resource files (not stored on the /app/data Docker volume)."""

from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent
HERO_BUNDLE_PATH = BENCHMARK_DIR / "hero_bundle.json"
GOLDEN_SET_PATH = BENCHMARK_DIR / "golden_set.json"
