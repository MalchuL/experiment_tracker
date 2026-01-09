from fastapi import APIRouter

router = APIRouter()


@router.get("/temp")
async def get_temp():
    return {"message": "Hello, World!"}
