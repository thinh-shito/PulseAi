from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.domain.models.user import User, TokenBlacklist
from app.infra.repositories.base_repository import BaseRepository

class UserRepository(BaseRepository[User]):
    """
    User Repository extending BaseRepository to support email queries and token blacklisting.
    """
    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        query = select(self.model).filter(self.model.email == email)
        result = await db.execute(query)
        return result.scalars().first()

    async def is_token_blacklisted(self, db: AsyncSession, jti: str) -> bool:
        query = select(TokenBlacklist).filter(TokenBlacklist.token_jti == jti)
        result = await db.execute(query)
        return result.scalars().first() is not None

    async def blacklist_token(
        self, db: AsyncSession, *, jti: str, user_id: str, expires_at
    ) -> TokenBlacklist:
        blacklist_entry = TokenBlacklist(
            token_jti=jti,
            user_id=user_id,
            expires_at=expires_at
        )
        db.add(blacklist_entry)
        await db.commit()
        await db.refresh(blacklist_entry)
        return blacklist_entry

user_repo = UserRepository()
