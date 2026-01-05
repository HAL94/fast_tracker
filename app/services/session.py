from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.jwt import hash_token
from app.domain.session import SessionBase
from app.dto.session import CreateSessionDto
from app.services.base import BaseService


class SessionService(BaseService):
    def __init__(self, session: AsyncSession):
        super().__init__(session=session)
        self._session = SessionBase

    def _get_model(self):
        return self._session

    async def create_session(self, data: CreateSessionDto, *, commit: bool = True) -> SessionBase:
        try:
            data_base = SessionBase(
                refresh_token_hash=hash_token(data.refresh_token),
                access_token_hash=hash_token(data.access_token),
                expires_at=data.expires_at,
                user_id=data.user_id,
            )
            return await self._session.create(self.session, data_base, commit=commit)
        except Exception as e:
            raise e

    async def logout_from_session(self, refresh_token: str) -> None:
        try:
            session = await self._session.get_one(
                self.session,
                hash_token(refresh_token),
                field=self._session.model.refresh_token_hash,
                return_as_base=True,
            )
            session.is_active = False
            await self.session.commit()
        except Exception:
            return None
