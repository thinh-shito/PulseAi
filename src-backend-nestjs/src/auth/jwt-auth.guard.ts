import {
  Injectable,
  CanActivate,
  ExecutionContext,
  UnauthorizedException,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { PrismaService } from '../database/prisma.service';
import type { FastifyRequest } from 'fastify';

interface JwtPayload {
  sub: string;
  jti?: string;
  type: string;
  exp: number;
  email: string;
  role: string;
}

interface AuthRequest extends FastifyRequest {
  user: Record<string, unknown>;
  jwtPayload: JwtPayload;
}

@Injectable()
export class JwtAuthGuard implements CanActivate {
  constructor(
    private jwtService: JwtService,
    private prisma: PrismaService,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest<AuthRequest>();
    let token = '';
    const authHeader = request.headers.authorization;
    if (authHeader && authHeader.startsWith('Bearer ')) {
      token = authHeader.split(' ')[1] ?? '';
    } else {
      const query = request.query as Record<string, string> | undefined;
      if (query && query.token) {
        token = query.token;
      }
    }

    if (!token) {
      throw new UnauthorizedException(
        'Missing or invalid Authorization header or query token',
      );
    }
    try {
      const payload = await this.jwtService.verifyAsync<JwtPayload>(token);
      if (payload.type !== 'access') {
        throw new UnauthorizedException('Invalid token type');
      }

      const blacklisted = await this.prisma.tokenBlacklist.findUnique({
        where: { tokenJti: payload.jti ?? '' },
      });
      if (blacklisted) {
        throw new UnauthorizedException('Token has been revoked');
      }

      const user = await this.prisma.user.findUnique({
        where: { id: payload.sub },
      });

      if (!user || !user.isActive) {
        throw new UnauthorizedException('User is inactive or does not exist');
      }

      request.user = user;
      request.jwtPayload = payload;
      return true;
    } catch {
      throw new UnauthorizedException('Token validation failed');
    }
  }
}
