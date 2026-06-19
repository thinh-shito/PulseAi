import { Injectable, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import * as bcrypt from 'bcryptjs';
import { User } from '../common/entities/user.entity';

@Injectable()
export class AuthService {
    constructor(
        @InjectRepository(User)
        private userRepository: Repository<User>,
        private jwtService: JwtService,
    ) { }

    async login(email: string, password: string): Promise<{ access_token: string; refresh_token: string; role: string }> {
        const user = await this.userRepository.findOne({ where: { email, is_active: true } });
        if (!user || !bcrypt.compareSync(password, user.hashed_password)) {
            throw new UnauthorizedException('Incorrect email or password');
        }

        const payload = { sub: user.id, email: user.email, role: user.role };
        return {
            access_token: this.jwtService.sign(payload, { expiresIn: '30m' }),
            refresh_token: this.jwtService.sign(payload, { expiresIn: '7d' }),
            role: user.role,
        };
    }

    getProfile(user: User) {
        return {
            id: user.id,
            email: user.email,
            full_name: user.full_name,
            role: user.role,
        };
    }
}