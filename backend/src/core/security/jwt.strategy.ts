import { Injectable, UnauthorizedException } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { ConfigService } from '@nestjs/config';
import { UserRepository } from '../../infra/repositories/user.repository';

export interface JwtPayload {
  sub: string; // user_id
  username: string;
  role: string;
}

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(
    private configService: ConfigService,
    private userRepository: UserRepository,
  ) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: configService.get<string>('jwt.secret'),
    });
  }

  async validate(payload: JwtPayload) {
    const user = await this.userRepository.findById(payload.sub);
    
    if (!user || !user.is_active) {
      throw new UnauthorizedException('User not found or inactive');
    }

    // Return user object that will be attached to request.user
    return {
      user_id: user.user_id,
      username: user.username,
      email: user.email,
      role: user.role,
      full_name: user.full_name,
    };
  }
}