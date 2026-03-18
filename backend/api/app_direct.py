from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Dict

app = FastAPI()

api_router = APIRouter(prefix="/api")

# In-memory user store and ID counter
users: Dict[int, dict] = {}
user_id_counter = 1

class UserCreate(BaseModel):
    username: str
    email: EmailStr

class User(UserCreate):
    id: int

@api_router.get("/health")
async def health_check():
    return {"status": "ok"}

@api_router.post("/users", response_model=User)
async def create_user(user_create: UserCreate):
    global user_id_counter
    user = User(id=user_id_counter, **user_create.dict())
    users[user_id_counter] = user
    user_id_counter += 1
    return user

@api_router.get("/users/{id}", response_model=User)
async def get_user(id: int):
    user = users.get(id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

app.include_router(api_router)  
