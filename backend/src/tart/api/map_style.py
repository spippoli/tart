"""`GET /api/map/style/{light,dark}.json`: the Instance's map style as the browser gets it."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from tart.config import Configuration
from tart.map.serving import TilesMissing, served_style

router = APIRouter()

TILES_MISSING = "tiles_missing"


def get_configuration(request: Request) -> Configuration:
    """The configuration loaded at startup."""
    return request.app.state.configuration


@router.get(
    "/api/map/style/{theme}.json",
    response_class=Response,
    responses={
        200: {
            "description": "The style, with absolute asset URLs and the current basemap extract",
            "content": {"application/json": {"schema": {"type": "object"}}},
        },
        304: {"description": "The style has not changed since the ETag sent"},
        503: {
            "description": "The style uses the local basemap, and there is no extract yet",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"code": {"const": TILES_MISSING}},
                        "required": ["code"],
                    }
                }
            },
        },
    },
)
def map_style(
    theme: Literal["light", "dark"],
    request: Request,
    configuration: Annotated[Configuration, Depends(get_configuration)],
) -> Response:
    """The map style of one theme, revalidated on every use (`no-cache` with an ETag)."""
    instance, environment = configuration.instance, configuration.environment
    headers = {"Cache-Control": "no-cache"}
    try:
        style = served_style(
            dict(instance.map_styles[theme]),
            str(environment.PUBLIC_BASE_URL),
            getattr(instance.settings.identity.accent, theme),
            environment.PMTILES_PATH,
        )
    except TilesMissing:
        return JSONResponse({"code": TILES_MISSING}, status_code=503, headers=headers)
    headers["ETag"] = style.etag
    sent = _etags(request.headers.get("If-None-Match", ""))
    if style.etag in sent or "*" in sent:
        return Response(status_code=304, headers=headers)
    return Response(style.body, media_type="application/json", headers=headers)


def _etags(header: str) -> set[str]:
    return {tag.strip().removeprefix("W/") for tag in header.split(",")}
