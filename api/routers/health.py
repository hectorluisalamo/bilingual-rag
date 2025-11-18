from fastapi import APIRouter

router = APIRouter()

@router.get("/live")
def live():
    return {"status": "ok"}

@router.get("/ready")
def ready():
    # TODO: test DB & Redis pings
    return {"status": "ok"}
