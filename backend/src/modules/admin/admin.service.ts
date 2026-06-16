import { Injectable, ConflictException } from '@nestjs/common';
import { UserRepository } from '../../infra/repositories/user.repository';
import { AuditLogRepository } from '../../infra/repositories/audit-log.repository';
import { HashingService } from '../../core/security/hashing.service';
import { CreateUserDto } from './dto/create-user.dto';
import { User } from '../../domain/models/user.entity';
import { AuditLog } from '../../domain/models/audit-log.entity';

@Injectable()
export class AdminService {
  constructor(
    private readonly userRepository: UserRepository,
    private readonly auditLogRepository: AuditLogRepository,
    private readonly hashingService: HashingService,
  ) {}

  async listUsers(skip?: number, limit?: number): Promise<User[]> {
    // findAll takes no parameters, so just return all and slice if needed
    const users = await this.userRepository.findAll();
    if (skip !== undefined || limit !== undefined) {
      const start = skip || 0;
      const end = limit ? start + limit : undefined;
      return users.slice(start, end);
    }
    return users;
  }

  async createUser(createUserDto: CreateUserDto): Promise<User> {
    // Check if email already exists
    const existingUser = await this.userRepository.findByEmail(createUserDto.email);
    if (existingUser) {
      throw new ConflictException('Email already registered');
    }

    // Hash password
    const passwordHash = await this.hashingService.hashPassword(createUserDto.password);

    // Create user
    const user = await this.userRepository.create({
      email: createUserDto.email,
      username: createUserDto.email.split('@')[0], // Generate username from email
      password_hash: passwordHash,
      full_name: createUserDto.full_name,
      role: createUserDto.role,
    });

    // Remove password hash from response
    const { password_hash, ...result } = user;
    return result as User;
  }

  async listAuditLogs(skip?: number, limit?: number): Promise<AuditLog[]> {
    const [logs] = await this.auditLogRepository.findAll(skip, limit);
    return logs;
  }
}