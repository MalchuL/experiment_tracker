from domain.scalars.service import ScalarsService, ScalarsServiceProtocol


async def get_scalars_service() -> ScalarsServiceProtocol:
    return ScalarsService()
