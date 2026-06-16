import { Injectable, UnauthorizedException } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { Strategy } from 'passport-local';
import { UserRepository } from '../../infra/repositories/user.repository';
import { HashingService } from './hashing.service';

@Injectable()
export class LocalStrategy extends PassportStrategy(Strategy) {
  constructor(
    private userRepository: UserRepository,
    private hashingService: HashingService,
  ) {
    super({
      usernameField: 'username',
      passwordField: 'password',
    });
  }

  async validate(username: string, password: string): Promise<any> {
    const user = await this.userRepository.findByUsername(username);

    if (!user) {
      throw new UnauthorizedException('Invalid credentials');
    }

    const isPasswordValid = await this.hashingService.comparePassword(
      password,
      user.password_hash,
    );

    if (!isPasswordValid) {
      throw new UnauthorizedException('Invalid credentials');
    }

    if (!user.is_active) {
      throw new UnauthorizedException('User account is inactive');
    }

    // Return user object (password_hash excluded)
    return {
      user_id: user.user_id,
      username: user.username,
      email: user.email,
      role: user.role,
      full_name: user.full_name,
    };
  }
}