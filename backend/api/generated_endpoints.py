from fastapi import APIRouter

router = APIRouter()


@router.post("/users")
async def create_user():
    return {"status": "ok", "handler": "create_user"}


@router.delete("/users/{id}")
async def delete_user():
    return {"status": "ok", "handler": "delete_user"}


@router.get("/health")
async def healthcheck():
    return {"status": "ok", "handler": "healthcheck"}


@router.get("/users/{id}")
async def read_user():
    return {"status": "ok", "handler": "read_user"}


@router.put("/users/{id}")
async def update_user():
    return {"status": "ok", "handler": "update_user"}
