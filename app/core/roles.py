from fastapi import Depends, HTTPException
from app.core.security import get_current_user

def require_role(*roles: str):
    def checker(user = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail="Forbidden"
            )
        return user
    return checker