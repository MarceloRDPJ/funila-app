from fastapi import APIRouter, Depends
from dependencies import get_current_user_role

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.get("/me")
def get_me(user_profile: dict = Depends(get_current_user_role)):
    return user_profile
