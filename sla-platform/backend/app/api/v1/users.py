from fastapi import APIRouter

router = APIRouter()


@router.post("/login")
async def login():
    return {"status": "ok"}


@router.post("/refresh")
async def refresh():
    return {"status": "ok"}


@router.get("/me")
async def get_current_user():
    return {"status": "ok", "user": None}


@router.get("/users", tags=["admin"])
async def list_users():
    return {"users": []}


@router.post("/users")
async def create_user():
    return {"status": "ok", "message": "not implemented"}
