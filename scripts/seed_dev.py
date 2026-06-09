"""
Dev seed script — creates default users for development and testing.
Run with: python scripts/seed_dev.py

WARNING: Never run this in production.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src-backend"))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.core.security import hash_password, Role
from app.domain.models.user import User
import uuid


SEED_USERS = [
    {
        "email": "admin@pulseai.hospital",
        "password": "AdminPass123!",
        "full_name": "System Administrator",
        "role": Role.ADMIN,
    },
    {
        "email": "doctor@pulseai.hospital",
        "password": "DoctorPass123!",
        "full_name": "Dr. Emily Chen",
        "role": Role.DOCTOR,
    },
    {
        "email": "viewer@pulseai.hospital",
        "password": "ViewerPass123!",
        "full_name": "Clinical Viewer",
        "role": Role.VIEWER,
    },
]


from sqlalchemy import select

async def seed():
    engine = create_async_engine(settings.database_url, echo=True)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as session:
        for user_data in SEED_USERS:
            # Check if user already exists by email
            stmt = select(User).where(User.email == user_data["email"])
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                existing_user.hashed_password = hash_password(user_data["password"])
                existing_user.full_name = user_data["full_name"]
                existing_user.role = user_data["role"]
                print(f"  🔄 Updated existing user: {user_data['email']} [{user_data['role'].value}]")
            else:
                user = User(
                    id=uuid.uuid4(),
                    email=user_data["email"],
                    hashed_password=hash_password(user_data["password"]),
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                )
                session.add(user)
                print(f"  ✅ Seeded user: {user_data['email']} [{user_data['role'].value}]")

        await session.commit()
    await engine.dispose()
    print("\n🎉 Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
