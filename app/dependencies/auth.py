import logging
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import APIKeyCookie, OAuth2PasswordBearer

from app.constants.roles import UserRole
from app.core.config import settings
from app.core.exceptions import NotFoundException, UnauthorizedException
from app.core.security.jwt import JwtManager, hash_token
from app.core.security.schema import JwtPayload, TokenType
from app.dependencies.db_session import DbSession
from app.domain.session import SessionBase
from app.domain.user import UserBase, UserWithoutPassword

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)


RtCookie = Annotated[str, Depends(APIKeyCookie(name=JwtManager.RT_COOKIE_KEY, auto_error=False))]
AtCookie = Annotated[str, Depends(APIKeyCookie(name=JwtManager.AT_COOKIE_KEY, auto_error=False))]


async def get_current_user(token_encoding: AtCookie, session: DbSession) -> UserWithoutPassword:
    try:
        logger.info("Checking user info")
        token = JwtManager.validate_at_cookie(token_encoding)
        logger.info(f"JWT TOKEN: {token}")
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        validated_payload = JwtPayload.model_validate(payload)

        if not validated_payload:
            raise UnauthorizedException
        if validated_payload.type != TokenType.AccessToken:
            raise UnauthorizedException

        email = validated_payload.sub
        if not email:
            raise UnauthorizedException

        fetched_session = await SessionBase.get_one(
            session, hash_token(token), field=SessionBase.model.access_token_hash
        )

        if not fetched_session.is_active:
            raise UnauthorizedException

        user_data = await UserBase.get_one(session, email, field=UserBase.model.email)
        if not user_data.is_active:
            raise UnauthorizedException

        return UserWithoutPassword.model_validate(user_data)
    except jwt.InvalidTokenError as e:
        logger.info(f"[get_current_user] Error occured: {e}")
        raise UnauthorizedException
    except NotFoundException:
        raise UnauthorizedException


async def get_current_active_user(
    current_user: Annotated[UserBase, Depends(get_current_user)],
) -> UserWithoutPassword:
    return current_user


CurrentUser = Annotated[UserWithoutPassword, Depends(get_current_active_user)]


class ValidateRole:
    def __init__(self, role: UserRole):
        self.role = role

    def __call__(self, user: CurrentUser):
        if user.role != self.role:
            raise UnauthorizedException
