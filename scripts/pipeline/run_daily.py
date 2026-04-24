import sys
import time

import fetch_metadata
import scrape_listeners
from common.logging import get_logger


logger = get_logger("run_daily")


def main() -> int:
    start = time.monotonic()

    try:
        metadata_exit = fetch_metadata.main()
    except Exception:
        logger.critical(
            "fetch_metadata raised unexpected exception",
            extra={"event": "fetch_metadata_crashed"},
            exc_info=True,
        )
        metadata_exit = 1

    try:
        scrape_exit = scrape_listeners.main()
    except Exception:
        logger.critical(
            "scrape_listeners raised unexpected exception",
            extra={"event": "scrape_listeners_crashed"},
            exc_info=True,
        )
        scrape_exit = 1

    duration = time.monotonic() - start
    logger.info(
        "daily_pipeline_complete",
        extra={
            "event": "daily_pipeline_complete",
            "metadata_exit": metadata_exit,
            "scrape_exit": scrape_exit,
            "duration_seconds": round(duration, 2),
        },
    )

    return 0 if metadata_exit == 0 and scrape_exit == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        logger.critical(
            "run_daily crashed",
            extra={"event": "run_daily_crashed"},
            exc_info=True,
        )
        sys.exit(1)
