"""Entry point of the `api` container: Uvicorn with the structured logs.

python -m tart.api
"""

import uvicorn

from tart.logs import logging_config


def main() -> None:
    uvicorn.run(
        "tart.api.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        log_config=logging_config(),
        access_log=False,
    )


if __name__ == "__main__":
    main()
