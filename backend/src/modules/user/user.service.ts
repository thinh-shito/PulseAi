import { Injectable, NotFoundException } from '@nestjs/common';
import { UserRepository } from '../../infra/repositories/user.repository';
import { User } from '../../domain/models/user.entity';

@Injectable()
export class UserService {
  constructor(private readonly userRepository: UserRepository) {}

  async getProfile(userId: string): Promise<User> {
    const user = await this.userRepository.findById(userId);
    if (!user) {
      throw new NotFoundException('User not found');
    }
    // Remove password hash before returning
    const { password_hash, ...result } = user;
    return result as User;
  }

  async findByUsername(username: string): Promise<User | null> {
    return this.userRepository.findByUsername(username);
  }
}