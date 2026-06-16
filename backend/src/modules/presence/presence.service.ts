import { Injectable, Logger } from '@nestjs/common';
import { RedisService } from '../../core/redis/redis.service';

const PRESENCE_BITMAP_KEY = 'presence:online';
const UID_COUNTER_KEY = 'presence:uid_counter';
const UID_MAP_PREFIX = 'presence:uid_map:';
const LAST_SEEN_PREFIX = 'presence:last_seen:';
const META_PREFIX = 'presence:meta:';
const PRESENCE_TTL = 90; // seconds

@Injectable()
export class PresenceService {
  private readonly logger = new Logger(PresenceService.name);

  constructor(private readonly redisService: RedisService) {}

  private get r() {
    return this.redisService.getClient();
  }

  async getOrCreateOffset(userUuid: string): Promise<number> {
    const mapKey = `${UID_MAP_PREFIX}${userUuid}`;
    const offsetStr = await this.r.get(mapKey);

    if (offsetStr !== null) {
      return parseInt(offsetStr, 10);
    }

    // Atomically allocate next offset
    let offset = await this.r.incr(UID_COUNTER_KEY);
    offset -= 1; // Make 0-indexed

    // Store bi-directional mapping
    await this.r.set(mapKey, offset.toString());
    await this.r.hset(`${META_PREFIX}${offset}`, 'uuid', userUuid);
    this.logger.debug(`Allocated bitmap offset ${offset} for user ${userUuid}`);
    return offset;
  }

  async getOffset(userUuid: string): Promise<number | null> {
    const val = await this.r.get(`${UID_MAP_PREFIX}${userUuid}`);
    return val !== null ? parseInt(val, 10) : null;
  }

  async heartbeat(userUuid: string, displayName = ''): Promise<void> {
    const offset = await this.getOrCreateOffset(userUuid);
    const nowIso = new Date().toISOString();

    const pipeline = this.r.pipeline();
    pipeline.setbit(PRESENCE_BITMAP_KEY, offset, 1);
    pipeline.set(`${LAST_SEEN_PREFIX}${userUuid}`, nowIso, 'EX', PRESENCE_TTL);
    await pipeline.exec();

    this.logger.debug(`Heartbeat: user ${userUuid} -> bit[${offset}]=1`);
  }

  async markOffline(userUuid: string): Promise<void> {
    const offset = await this.getOffset(userUuid);
    if (offset === null) {
      return;
    }

    const pipeline = this.r.pipeline();
    pipeline.setbit(PRESENCE_BITMAP_KEY, offset, 0);
    pipeline.del(`${LAST_SEEN_PREFIX}${userUuid}`);
    await pipeline.exec();

    this.logger.log(`User ${userUuid} marked offline (logout)`);
  }

  async isOnline(userUuid: string): Promise<boolean> {
    const offset = await this.getOffset(userUuid);
    if (offset === null) {
      return false;
    }

    const bit = await this.r.getbit(PRESENCE_BITMAP_KEY, offset);
    if (!bit) {
      return false;
    }

    const lastSeen = await this.r.get(`${LAST_SEEN_PREFIX}${userUuid}`);
    if (lastSeen === null) {
      // TTL expired -> clean the stale bit
      await this.r.setbit(PRESENCE_BITMAP_KEY, offset, 0);
      return false;
    }

    return true;
  }

  async getOnlineCount(): Promise<number> {
    const count = await this.r.bitcount(PRESENCE_BITMAP_KEY);
    return count;
  }

  async getPresenceBulk(userUuids: string[]): Promise<Record<string, boolean>> {
    if (!userUuids || userUuids.length === 0) {
      return {};
    }

    const offsets: Record<string, number> = {};
    for (const uuid of userUuids) {
      const off = await this.getOffset(uuid);
      if (off !== null) {
        offsets[uuid] = off;
      }
    }

    if (Object.keys(offsets).length === 0) {
      const result: Record<string, boolean> = {};
      for (const uuid of userUuids) {
        result[uuid] = false;
      }
      return result;
    }

    const pipeline = this.r.pipeline();
    for (const uuid of userUuids) {
      if (offsets[uuid] !== undefined) {
        pipeline.getbit(PRESENCE_BITMAP_KEY, offsets[uuid]);
        pipeline.get(`${LAST_SEEN_PREFIX}${uuid}`);
      }
    }

    const results = await pipeline.exec();
    const presence: Record<string, boolean> = {};
    let idx = 0;

    for (const uuid of userUuids) {
      if (offsets[uuid] !== undefined && results) {
        const bitResult = results[idx]?.[1];
        const lastSeenResult = results[idx + 1]?.[1];
        idx += 2;

        // ioredis results are string/number or null
        const bit = bitResult !== null && bitResult !== undefined ? parseInt(bitResult as string, 10) : 0;
        const lastSeen = lastSeenResult as string | null;

        const isUserOnline = !!bit && lastSeen !== null;
        presence[uuid] = isUserOnline;

        if (bit && lastSeen === null) {
          await this.r.setbit(PRESENCE_BITMAP_KEY, offsets[uuid], 0);
        }
      } else {
        presence[uuid] = false;
      }
    }

    return presence;
  }

  async getLastSeen(userUuid: string): Promise<string | null> {
    return await this.r.get(`${LAST_SEEN_PREFIX}${userUuid}`);
  }

  async getStats() {
    const onlineCount = await this.getOnlineCount();
    const totalRegisteredStr = await this.r.get(UID_COUNTER_KEY);
    return {
      online_users: onlineCount,
      total_registered: totalRegisteredStr ? parseInt(totalRegisteredStr, 10) : 0,
      bitmap_key: PRESENCE_BITMAP_KEY,
      ttl_seconds: PRESENCE_TTL,
    };
  }
}