"""
Redis Presence Service — User Online/Offline tracking using Bitmaps.

Architecture:
  - Key "presence:online" → Bitmap, 1 bit per user numeric ID
  - Key "presence:uid_map:<uuid>" → String, maps UUID → int offset
  - Key "presence:uid_counter" → String, auto-increment counter for offsets
  - Key "presence:last_seen:<uuid>" → String, ISO timestamp of last heartbeat
  - Key "presence:meta:<offset>" → Hash, stores uuid + display name for BITCOUNT queries

Why Bitmap?
  - 1 million users = 1 MB of memory (vs ~50 MB with hashes)
  - BITCOUNT is O(n/8) — extremely fast
  - SETBIT/GETBIT are O(1)
"""

import logging
from datetime import datetime, timezone
from typing import Optional
import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── Redis Keys ──────────────────────────────────────────────────────────────
PRESENCE_BITMAP_KEY = "presence:online"          # Main bitmap
UID_COUNTER_KEY = "presence:uid_counter"          # Auto-increment
UID_MAP_PREFIX = "presence:uid_map:"              # uuid → int offset
LAST_SEEN_PREFIX = "presence:last_seen:"          # uuid → ISO datetime
META_PREFIX = "presence:meta:"                    # offset → {uuid, name}
# seconds — offline if no heartbeat
PRESENCE_TTL = 90

# ─── Redis Client (lazy singleton) ───────────────────────────────────────────
_redis_client: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    """Return (and lazily create) the async Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


# ─── Core Service ────────────────────────────────────────────────────────────

class PresenceService:
    """
    Redis Bitmap-based presence tracker.

    Each user UUID is assigned a unique integer offset (0-indexed).
    The bitmap stores 1 = online, 0 = offline for each offset.

    Example for 5 users:
        Offset: 0  1  2  3  4
        Bits:   1  0  1  1  0
        → users 0, 2, 3 are online (3 total = BITCOUNT)
    """

    def __init__(self, redis: aioredis.Redis):
        self.r = redis

    # ── Offset Management ────────────────────────────────────────────────────

    async def _get_or_create_offset(self, user_uuid: str) -> int:
        """
        Get the integer bitmap offset for a UUID.
        If the UUID has never been seen, allocate the next available offset.
        """
        map_key = f"{UID_MAP_PREFIX}{user_uuid}"
        offset_str = await self.r.get(map_key)

        if offset_str is not None:
            return int(offset_str)

        # Atomically allocate next offset
        offset = await self.r.incr(UID_COUNTER_KEY)
        offset -= 1  # Make 0-indexed

        # Store bi-directional mapping
        await self.r.set(map_key, str(offset))
        await self.r.hset(f"{META_PREFIX}{offset}", mapping={
            "uuid": user_uuid,
        })
        logger.debug(f"Allocated bitmap offset {offset} for user {user_uuid}")
        return offset

    async def _get_offset(self, user_uuid: str) -> Optional[int]:
        """Get existing offset for UUID, or None if not registered."""
        val = await self.r.get(f"{UID_MAP_PREFIX}{user_uuid}")
        return int(val) if val is not None else None

    # ── Heartbeat / Mark Online ───────────────────────────────────────────────

    async def heartbeat(self, user_uuid: str, display_name: str = "") -> None:
        """
        Mark a user as online.
        Called on login and periodically (every ~30s) by the frontend.

        Operations:
          SETBIT presence:online <offset> 1   → mark online in bitmap
          SET presence:last_seen:<uuid> <iso> → update last seen
          EXPIRE presence:last_seen:<uuid> 90 → auto-expire if no heartbeat
        """
        offset = await self._get_or_create_offset(user_uuid)

        pipe = self.r.pipeline()
        # Set the bit — O(1)
        pipe.setbit(PRESENCE_BITMAP_KEY, offset, 1)
        # Update last seen with TTL (auto-offline after 90s of silence)
        now_iso = datetime.now(timezone.utc).isoformat()
        pipe.set(f"{LAST_SEEN_PREFIX}{user_uuid}", now_iso, ex=PRESENCE_TTL)
        await pipe.execute()

        logger.debug(f"Heartbeat: user {user_uuid} → bit[{offset}]=1")

    async def mark_offline(self, user_uuid: str) -> None:
        """
        Mark a user as offline immediately (e.g., on logout).

        Operations:
          SETBIT presence:online <offset> 0   → clear bit
          DEL presence:last_seen:<uuid>       → remove last seen
        """
        offset = await self._get_offset(user_uuid)
        if offset is None:
            return  # Never seen — nothing to do

        pipe = self.r.pipeline()
        pipe.setbit(PRESENCE_BITMAP_KEY, offset, 0)
        pipe.delete(f"{LAST_SEEN_PREFIX}{user_uuid}")
        await pipe.execute()

        logger.info(f"User {user_uuid} marked offline (logout)")

    # ── Query Online Status ───────────────────────────────────────────────────

    async def is_online(self, user_uuid: str) -> bool:
        """
        Check if a specific user is online.

        Uses GETBIT — O(1).
        Also validates the last_seen TTL hasn't expired (stale bit cleanup).
        """
        offset = await self._get_offset(user_uuid)
        if offset is None:
            return False

        # Check bitmap bit (O1)
        bit = await self.r.getbit(PRESENCE_BITMAP_KEY, offset)
        if not bit:
            return False

        # Validate last_seen TTL — auto-clean stale bits
        last_seen = await self.r.get(f"{LAST_SEEN_PREFIX}{user_uuid}")
        if last_seen is None:
            # TTL expired → clean the stale bit
            await self.r.setbit(PRESENCE_BITMAP_KEY, offset, 0)
            return False

        return True

    async def get_online_count(self) -> int:
        """
        Count total online users.

        Uses BITCOUNT — O(n/8), extremely fast even for millions of users.
        BITCOUNT "presence:online" returns number of set bits (1s).
        """
        count = await self.r.bitcount(PRESENCE_BITMAP_KEY)
        return count

    async def get_presence_bulk(self, user_uuids: list[str]) -> dict[str, bool]:
        """
        Get online status for a list of users in a single pipeline.

        Uses Redis pipeline to batch GETBIT + GET last_seen in one round-trip.
        Returns {uuid: True/False} mapping.
        """
        if not user_uuids:
            return {}

        # Get all offsets for users that have them
        offsets = {}
        for uuid in user_uuids:
            off = await self._get_offset(uuid)
            if off is not None:
                offsets[uuid] = off

        # If no users have offsets, they are all offline
        if not offsets:
            return {uuid: False for uuid in user_uuids}

        # Pipeline GETBIT and last_seen checks only for existing offsets
        pipe = self.r.pipeline()
        for uuid, offset in offsets.items():
            pipe.getbit(PRESENCE_BITMAP_KEY, offset)
            pipe.get(f"{LAST_SEEN_PREFIX}{uuid}")
        results = await pipe.execute()

        presence = {}
        idx = 0
        for uuid in user_uuids:
            if uuid in offsets:
                bit = results[idx]
                last_seen = results[idx + 1]
                idx += 2
                is_user_online = bool(bit) and (last_seen is not None)
                presence[uuid] = is_user_online

                # Stale bit cleanup: if bit is 1 but last_seen has expired (is None), reset bit to 0
                if bit and last_seen is None:
                    await self.r.setbit(PRESENCE_BITMAP_KEY, offsets[uuid], 0)
            else:
                presence[uuid] = False

        return presence

    async def get_last_seen(self, user_uuid: str) -> Optional[str]:
        """Return ISO timestamp of last heartbeat, or None if offline."""
        return await self.r.get(f"{LAST_SEEN_PREFIX}{user_uuid}")

    async def get_stats(self) -> dict:
        """
        Return overall presence statistics.
        Used by monitoring / admin dashboard.
        """
        online_count = await self.get_online_count()
        total_registered = await self.r.get(UID_COUNTER_KEY)
        return {
            "online_users": online_count,
            "total_registered": int(total_registered) if total_registered else 0,
            "bitmap_key": PRESENCE_BITMAP_KEY,
            "ttl_seconds": PRESENCE_TTL,
        }


# ─── FastAPI Dependency ───────────────────────────────────────────────────────

async def get_presence_service() -> PresenceService:
    """FastAPI dependency — returns a PresenceService bound to the Redis client."""
    return PresenceService(get_redis())
