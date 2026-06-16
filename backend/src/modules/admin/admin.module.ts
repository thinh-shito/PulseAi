import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AdminController } from './admin.controller';
import { AdminService } from './admin.service';
import { User } from '../../domain/models/user.entity';
import { AuditLog } from '../../domain/models/audit-log.entity';
import { UserRepository } from '../../infra/repositories/user.repository';
import { AuditLogRepository } from '../../infra/repositories/audit-log.repository';
import { HashingService } from '../../core/security/hashing.service';

@Module({
  imports: [
    TypeOrmModule.forFeature([User, AuditLog]),
  ],
  controllers: [AdminController],
  providers: [
    AdminService,
    UserRepository,
    AuditLogRepository,
    HashingService,
  ],
  exports: [AdminService],
})
export class AdminModule {}
