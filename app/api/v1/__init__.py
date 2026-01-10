from fastapi import APIRouter

from .activity import activity_router
from .auth import auth_router
from .journal import journal_router

v1_router = APIRouter(prefix="/v1")


@v1_router.get("/welcome")
def welcome():
    return {"Welcome": "to your seed project"}


v1_router.include_router(auth_router)
v1_router.include_router(activity_router)
v1_router.include_router(journal_router)
