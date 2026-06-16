import {
  Controller,
  Post,
  Delete,
  Get,
  Body,
  Query,
  Sse,
  UseGuards,
  MessageEvent,
  ForbiddenException,
  HttpCode,
  HttpStatus,
} from '@nestjs/common';
import { JwtAuthGuard } from '../../common/guards/jwt-auth.guard';
import { RolesGuard, UserRole } from '../../core/security/roles.guard';
import { CurrentUser } from '../../common/decorators/user.decorator';
import { User } from '../../domain/models/user.entity';
import { PresenceService } from './presence.service';
import { Observable, interval } from 'rxjs';
import { switchMap } from 'rxjs/operators';

class BulkPresenceRequest {
  user_ids: string[];
}

@UseGuards(JwtAuthGuard, RolesGuard)
@Controller('presence')
export class PresenceController {
  constructor(private readonly presenceService: PresenceService) {}

  @Post('heartbeat')
  async heartbeat(@CurrentUser() user: User) {
    await this.presenceService.heartbeat(user.user_id, user.full_name);
    return {
      online: true,
      user_id: user.user_id,
      message: 'Presence updated',
    };
  }

  @Delete('offline')
  @HttpCode(HttpStatus.NO_CONTENT)
  async markOffline(@CurrentUser() user: User) {
    await this.presenceService.markOffline(user.user_id);
  }

  @Get('me')
  async getMyStatus(@CurrentUser() user: User) {
    const online = await this.presenceService.isOnline(user.user_id);
    const lastSeen = await this.presenceService.getLastSeen(user.user_id);
    return {
      user_id: user.user_id,
      online,
      last_seen: lastSeen,
    };
  }

  @Post('users')
  async getBulkPresence(
    @CurrentUser() user: User,
    @Body() body: BulkPresenceRequest,
  ) {
    if (user.role === UserRole.VIEWER) {
      const hasOthers = body.user_ids.some((uid) => uid !== user.user_id);
      if (hasOthers) {
        throw new ForbiddenException('Viewers can only query their own presence');
      }
    }
    return this.presenceService.getPresenceBulk(body.user_ids);
  }

  @Get('stats')
  async getPresenceStats() {
    return this.presenceService.getStats();
  }

  @Get('stream')
  @Sse()
  streamPresence(
    @Query('interval') intervalParam = '10',
  ): Observable<MessageEvent> {
    let intervalSec = parseInt(intervalParam, 10);
    if (isNaN(intervalSec) || intervalSec < 5) {
      intervalSec = 5;
    } else if (intervalSec > 60) {
      intervalSec = 60;
    }

    return interval(intervalSec * 1000).pipe(
      switchMap(async () => {
        const stats = await this.presenceService.getStats();
        return {
          data: {
            online_users: stats.online_users,
            total_registered: stats.total_registered,
            timestamp: new Date().toISOString(),
          },
        };
      }),
    );
  }
}