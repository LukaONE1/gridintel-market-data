
"""GRIDINTEL NFL historical data loader v0.1.

Uses nflverse play-by-play data.
Historical research only; not a live prediction feed.
"""

import io

import httpx

NFLVERSE_PBP_2025 = (
    "https://github.com/nflverse/nflverse-data/"
    "releases/download/pbp/play_by_play_2025.parquet"
)


def download_pbp_2025() -> bytes:
    """Download the 2025 NFL play-by-play Parquet file."""
    with httpx.Client(
        follow_redirects=True,
        timeout=120.0,
    ) as client:
        response = client.get(NFLVERSE_PBP_2025)
        response.raise_for_status()
        return response.content


def inspect_pbp_columns() -> dict:
    """Read the Parquet schema without loading all rows."""
    import pyarrow.parquet as pq

    data = download_pbp_2025()
    parquet_file = pq.ParquetFile(io.BytesIO(data))

    return {
        "source": "nflverse",
        "season": 2025,
        "row_count": parquet_file.metadata.num_rows,
        "columns": parquet_file.schema_arrow.names,
    }
