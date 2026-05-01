import logging
import traceback

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.core.security.jwt import JwtManager, hash_token, verify_password
from app.core.security.schema import JwtPayload, TokenType
from app.domain.user import UserBase
from app.dto.auth import LoginUserDto, UserSession
from app.dto.session import CreateSessionDto
from app.repositories.user_repository import UserRepository
from app.services.base import BaseService
from app.services.session import SessionService

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)


class AuthService(BaseService):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self._user_repo = UserRepository(session)
        self._session_service = SessionService(session)

    async def login(self, data: LoginUserDto) -> UserSession:
        try:
            found_user: UserBase = await self._user_repo.get_one([UserBase.model.email == data.email])

            is_match = verify_password(data.password, found_user.hashed_password)

            if not is_match:
                raise UnauthorizedException()

            access_token = JwtManager.create_token(subject=found_user.email, token_type=TokenType.AccessToken)
            refresh_token = JwtManager.create_token(subject=found_user.email, token_type=TokenType.RefreshToken)

            user_session = await self._session_service.create_session(
                CreateSessionDto(
                    refresh_token=refresh_token,
                    access_token=access_token,
                    expires_at=JwtManager.get_expiry(TokenType.RefreshToken),
                    user_id=found_user.id,
                    tenant_id=found_user.tenant_id,
                )
            )
            return UserSession(access_token=access_token, refresh_token=refresh_token, session_id=user_session.id)
        except Exception as e:
            logger.error(f"[AuthService-login]: {e}")
            raise e

    async def refresh_session(self, rt_encoding: str) -> UserSession:
        try:
            credentials_exception = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            rt_token = JwtManager.validate_rt_cookie(rt_encoding)
            jwt_payload: JwtPayload = JwtManager.verify_token(rt_token)

            if jwt_payload.type != TokenType.RefreshToken:
                raise credentials_exception

            email = jwt_payload.sub
            found_user = await self._user_repo.get_one([email == UserBase.model.email])

            user_session = await self._session_service.get_session_by_rt_hash(hash_token(rt_token))
            if not user_session.is_active:
                raise credentials_exception

            new_access_token = JwtManager.create_token(subject=email, token_type=TokenType.AccessToken)
            new_refresh_token = JwtManager.create_token(subject=email, token_type=TokenType.RefreshToken)

            user_session.is_active = False
            new_session = await self._session_service.create_session(
                CreateSessionDto(
                    refresh_token=new_refresh_token,
                    access_token=new_access_token,
                    expires_at=JwtManager.get_expiry(TokenType.RefreshToken),
                    user_id=found_user.id,
                    tenant_id=found_user.tenant_id,
                )
            )
            return UserSession(
                access_token=new_access_token, refresh_token=new_refresh_token, session_id=new_session.id
            )
        except Exception as e:
            logger.error(f"[AuthService-refresh]: {e}")
            traceback.print_exc()
            raise e
