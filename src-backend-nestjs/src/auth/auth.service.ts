import { Injectable, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { PrismaService } from '../database/prisma.service';
import { LoginDto } from './dto/login.dto';
import * as bcrypt from 'bcrypt';
import { v4 as uuidv4 } from 'uuid';

interface JwtPayload {
  sub: string;
  jti?: string;
  type: string;
  exp: number;
  email: string;
  role: string;
}

@Injectable()
export class AuthService {
  constructor(
    private prisma: PrismaService,
    private jwtService: JwtService,
  ) {}

  async hashPassword(password: string): Promise<string> {
    return bcrypt.hash(password, 10);
  }

  async verifyPassword(password: string, hash: string): Promise<boolean> {
    return bcrypt.compare(password, hash);
  }

  async login(loginDto: LoginDto) {
    const user = await this.prisma.user.findUnique({
      where: { email: loginDto.email },
    });

    if (!user || !user.isActive) {
      throw new UnauthorizedException('Invalid email or password');
    }

    const isPasswordValid = await this.verifyPassword(
      loginDto.password,
      user.hashedPassword,
    );
    if (!isPasswordValid) {
      throw new UnauthorizedException('Invalid email or password');
    }

    const payload = {
      sub: user.id,
      email: user.email,
      role: user.role,
    };

    const accessTokenJti = uuidv4();
    const refreshTokenJti = uuidv4();

    // 30 min access token
    const accessToken = await this.jwtService.signAsync(
      { ...payload, type: 'access', jti: accessTokenJti },
      { expiresIn: '30m' },
    );

    // 7 days refresh token
    const refreshToken = await this.jwtService.signAsync(
      { sub: user.id, type: 'refresh', jti: refreshTokenJti },
      { expiresIn: '7d' },
    );

    return {
      access_token: accessToken,
      refresh_token: refreshToken,
      user: {
        id: user.id,
        email: user.email,
        full_name: user.fullName,
        role: user.role,
      },
    };
  }

  async logout(tokenJti: string, userId: string, exp: number) {
    // exp is epoch timestamp in seconds
    const expiresAt = new Date(exp * 1000);
    await this.prisma.tokenBlacklist.create({
      data: {
        tokenJti,
        userId,
        expiresAt,
      },
    });
    return { message: 'Logged out successfully' };
  }

  async refresh(refreshToken: string) {
    try {
      const payload =
        await this.jwtService.verifyAsync<JwtPayload>(refreshToken);
      if (payload.type !== 'refresh') {
        throw new UnauthorizedException('Invalid token type');
      }

      // Check blacklist
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

      const newAccessTokenJti = uuidv4();
      const newAccessToken = await this.jwtService.signAsync(
        {
          sub: user.id,
          email: user.email,
          role: user.role,
          type: 'access',
          jti: newAccessTokenJti,
        },
        { expiresIn: '30m' },
      );

      return { access_token: newAccessToken };
    } catch {
      throw new UnauthorizedException('Invalid refresh token');
    }
  }
}
