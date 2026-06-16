import { Injectable, UnauthorizedException, ConflictException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { UserRepository } from '../../infra/repositories/user.repository';
import { HashingService } from '../../core/security/hashing.service';
import { LoginDto } from './dto/login.dto';
import { RegisterDto } from './dto/register.dto';
import { TokenResponseDto } from './dto/token-response.dto';
import { UserRole } from '../../core/security/roles.guard';

@Injectable()
export class AuthService {
  constructor(
    private readonly userRepository: UserRepository,
    private readonly hashingService: HashingService,
    private readonly jwtService: JwtService,
  ) {}

  async register(registerDto: RegisterDto): Promise<TokenResponseDto> {
    // Check if username already exists
    const existingUser = await this.userRepository.findByUsername(registerDto.username);
    if (existingUser) {
      throw new ConflictException('Username already exists');
    }

    // Check if email already exists
    const existingEmail = await this.userRepository.findByEmail(registerDto.email);
    if (existingEmail) {
      throw new ConflictException('Email already exists');
    }

    // Hash password
    const password_hash = await this.hashingService.hashPassword(registerDto.password);

    // Create user
    const user = await this.userRepository.create({
      username: registerDto.username,
      email: registerDto.email,
      password_hash,
      role: registerDto.role || UserRole.VIEWER,
      full_name: registerDto.full_name,
    });

    // Generate JWT token
    const payload = { sub: user.user_id, username: user.username, role: user.role };
    const access_token = await this.jwtService.signAsync(payload);

    return {
      access_token,
      user: {
        user_id: user.user_id,
        username: user.username,
        email: user.email,
        role: user.role,
        full_name: user.full_name,
      },
    };
  }

  async login(loginDto: LoginDto): Promise<TokenResponseDto> {
    // Find user by username
    const user = await this.userRepository.findByUsername(loginDto.username);
    if (!user) {
      throw new UnauthorizedException('Invalid credentials');
    }

    // Verify password
    const isPasswordValid = await this.hashingService.comparePassword(
      loginDto.password,
      user.password_hash,
    );
    if (!isPasswordValid) {
      throw new UnauthorizedException('Invalid credentials');
    }

    // Check if user is active
    if (!user.is_active) {
      throw new UnauthorizedException('User account is inactive');
    }

    // Generate JWT token
    const payload = { sub: user.user_id, username: user.username, role: user.role };
    const access_token = await this.jwtService.signAsync(payload);

    return {
      access_token,
      user: {
        user_id: user.user_id,
        username: user.username,
        email: user.email,
        role: user.role,
        full_name: user.full_name,
      },
    };
  }

  async validateUser(username: string, password: string): Promise<any> {
    const user = await this.userRepository.findByUsername(username);
    if (!user) {
      return null;
    }

    const isPasswordValid = await this.hashingService.comparePassword(password, user.password_hash);
    if (!isPasswordValid) {
      return null;
    }

    if (!user.is_active) {
      return null;
    }

    const { password_hash, ...result } = user;
    return result;
  }
}