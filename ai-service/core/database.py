"""Database connection pool management using asyncpg."""
import asyncpg
from typing import Optional
from .config import settings


class DatabasePool:
    """Singleton database connection pool manager."""
    
    _pool: Optional[asyncpg.Pool] = None
    
    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        """Get or create the database connection pool."""
        if cls._pool is None:
            cls._pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60,
            )
        return cls._pool
    
    @classmethod
    async def close_pool(cls) -> None:
        """Close the database connection pool."""
        if cls._pool is not None:
            await cls._pool.close()
            cls._pool = None


async def init_db() -> None:
    """Initialize database connection and verify schema exists."""
    pool = await DatabasePool.get_pool()
    
    async with pool.acquire() as conn:
        # Verify required tables exist
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('conversations_v2', 'messages_v2', 'exported_files_v2')
        """)
        
        if len(tables) < 3:
            raise RuntimeError(
                "Required database tables not found. "
                "Please run migrations on the backend service first."
            )


async def get_db_connection():
    """Dependency for getting a database connection from the pool."""
    pool = await DatabasePool.get_pool()
    async with pool.acquire() as connection:
        yield connection