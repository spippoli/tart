"""The environment: every secret and all infrastructure wiring (ADR 0009).

The configuration directory is secret-free and identical across deployments; what
differs between them, and every credential, is read from these variables.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    SecretStr,
    model_validator,
)

CONFIG_DIR = "CONFIG_DIR"
DEFAULT_CONFIG_DIR = Path("/config")
"""Where the `api` image reads the configuration directory, mounted read-only."""
PMTILES_PATH = "PMTILES_PATH"
DEFAULT_PMTILES_PATH = Path("/data/tiles")
"""The data volume of the basemap extracts, which Caddy serves at `/tiles/`."""


class Environment(BaseModel):
    """The variables `api` and `worker` read, by their environment names."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    DATABASE_URL: SecretStr
    PUBLIC_BASE_URL: HttpUrl
    SESSION_KEY: Annotated[SecretStr, Field(min_length=32)]

    STORAGE_BACKEND: Literal["filesystem", "s3"] = "filesystem"
    STORAGE_PATH: Path = Path("/data/storage")
    S3_ENDPOINT_URL: HttpUrl | None = None
    S3_REGION: str | None = None
    S3_BUCKET: str | None = None
    S3_ACCESS_KEY_ID: SecretStr | None = None
    S3_SECRET_ACCESS_KEY: SecretStr | None = None

    SMTP_HOST: str
    SMTP_PORT: Annotated[int, Field(ge=1, le=65535)] = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: SecretStr | None = None

    PMTILES_PATH: Path = DEFAULT_PMTILES_PATH

    @model_validator(mode="after")
    def _s3_is_complete(self) -> Self:
        if self.STORAGE_BACKEND == "s3":
            missing = [
                name
                for name in (
                    "S3_ENDPOINT_URL",
                    "S3_REGION",
                    "S3_BUCKET",
                    "S3_ACCESS_KEY_ID",
                    "S3_SECRET_ACCESS_KEY",
                )
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(f"STORAGE_BACKEND=s3 also needs {', '.join(missing)}")
        return self


def config_dir(environ: Mapping[str, str]) -> Path:
    return Path(environ.get(CONFIG_DIR) or DEFAULT_CONFIG_DIR)


def pmtiles_path(environ: Mapping[str, str]) -> Path:
    return Path(environ.get(PMTILES_PATH) or DEFAULT_PMTILES_PATH)
