import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import fetch_metadata
import scrape_listeners


ARTIST_ID_LENGTH = 22
ARTIST_LIST_PATH = Path(__file__).parent / "artist_list.json"


def _extract_spotify_id(value: str) -> str:
    candidate = value.strip()

    if not candidate:
        raise ValueError("Empty artist argument.")

    if candidate.startswith("spotify:artist:"):
        spotify_id = candidate.removeprefix("spotify:artist:")
        return _validate_spotify_id(spotify_id, value)

    if candidate.startswith("http://") or candidate.startswith("https://"):
        parsed = urlparse(candidate)
        path_parts = [part for part in parsed.path.split("/") if part]

        for index, part in enumerate(path_parts):
            if part == "artist" and index + 1 < len(path_parts):
                return _validate_spotify_id(path_parts[index + 1], value)

        raise ValueError(f"Unsupported Spotify artist URL: {value}")

    return _validate_spotify_id(candidate, value)


def _validate_spotify_id(spotify_id: str, original: str) -> str:
    if len(spotify_id) != ARTIST_ID_LENGTH or not spotify_id.isalnum():
        raise ValueError(f"Invalid Spotify artist ID: {original}")

    return spotify_id


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add Spotify artists to artist_list.json and fetch their metadata and listeners.",
    )
    parser.add_argument("artists", nargs="+", help="Spotify artist URLs, URIs, or bare IDs.")
    return parser.parse_args()


def _load_artist_list() -> list[str]:
    if not ARTIST_LIST_PATH.is_file():
        return []

    raw = ARTIST_LIST_PATH.read_text(encoding="utf-8")
    data = json.loads(raw)

    if not isinstance(data, list):
        raise RuntimeError("artist_list.json must contain a JSON array of Spotify artist IDs.")

    return [item for item in data if isinstance(item, str) and item]


def _save_artist_list(artist_ids: list[str]) -> None:
    ARTIST_LIST_PATH.write_text(json.dumps(artist_ids, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = _parse_args()

    try:
        requested_ids = [_extract_spotify_id(value) for value in args.artists]
        existing_ids = _load_artist_list()
    except Exception as error:  # noqa: BLE001
        print(f"Failed to prepare artist list: {error}", file=sys.stderr)
        return 1

    seen = set(existing_ids)
    new_ids: list[str] = []

    for spotify_id in requested_ids:
        if spotify_id in seen:
            continue

        seen.add(spotify_id)
        new_ids.append(spotify_id)

    all_ids = existing_ids + new_ids

    try:
        if new_ids:
            _save_artist_list(all_ids)
    except Exception as error:  # noqa: BLE001
        print(f"Failed to update artist_list.json: {error}", file=sys.stderr)
        return 1

    metadata_exit = fetch_metadata.main(new_ids) if new_ids else 0
    scrape_exit = scrape_listeners.main(spotify_ids=new_ids) if new_ids else 0

    print(f"Added {len(new_ids)} new artists to catalog. Catalog now contains {len(all_ids)} artists.")

    return 0 if metadata_exit == 0 and scrape_exit == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
