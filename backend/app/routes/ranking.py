from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/ranking")
def get_ranking() -> list[dict]:
    raise HTTPException(status_code=501, detail="No implementat")
