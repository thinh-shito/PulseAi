import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from '../../domain/models/user.entity';
import { UserRole } from '../../core/security/roles.guard';

@Injectable()
export class UserRepository {
  constructor(
    @InjectRepository(User)
    private readonly repository: Repository<User>,
  ) {}

  async findAll(): Promise<User[]> {
    return this.repository.find({
      select: ['user_id', 'username', 'email', 'role', 'full_name', 'is_active', 'created_at'],
    });
  }

  async findById(user_id: string): Promise<User | null> {
    return this.repository.findOne({
      where: { user_id },
      select: ['user_id', 'username', 'email', 'role', 'full_name', 'is_active', 'created_at'],
    });
  }

  async findByIdWithPassword(user_id: string): Promise<User | null> {
    return this.repository.findOne({
      where: { user_id },
    });
  }

  async findByUsername(username: string): Promise<User | null> {
    return this.repository.findOne({
      where: { username },
    });
  }

  async findByEmail(email: string): Promise<User | null> {
    return this.repository.findOne({
      where: { email },
      select: ['user_id', 'username', 'email', 'role', 'full_name', 'is_active', 'created_at'],
    });
  }

  async create(userData: {
    username: string;
    email: string;
    password_hash: string;
    role?: UserRole;
    full_name?: string;
  }): Promise<User> {
    const user = this.repository.create(userData);
    return this.repository.save(user);
  }

  async update(user_id: string, updates: Partial<User>): Promise<User | null> {
    await this.repository.update(user_id, updates);
    return this.findById(user_id);
  }

  async delete(user_id: string): Promise<boolean> {
    const result = await this.repository.delete(user_id);
    return result.affected !== undefined && result.affected !== null && result.affected > 0;
  }

  async setInactive(user_id: string): Promise<User | null> {
    return this.update(user_id, { is_active: false });
  }

  async count(): Promise<number> {
    return this.repository.count();
  }
}