from domain.scalars.client import ScalarsServiceClient
from domain.scalars.service import (
    NoOpScalarsService,
    ScalarsService,
    ScalarsServiceProtocol,
)
from config.settings import get_settings


async def get_scalars_service() -> ScalarsServiceProtocol:
    settings = get_settings()
    scalars_service_url = settings.scalars_service_url
    if scalars_service_url:
        client = ScalarsServiceClient(scalars_service_url)
        return ScalarsService(client)
    else:
        return NoOpScalarsService()
