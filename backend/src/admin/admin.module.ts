import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AdminService } from './admin.service';
import { AdminController } from './admin.controller';
import { User } from '../common/entities/user.entity';
import { AuditLog } from '../common/entities/audit-log.entity';
import { PATemplate } from '../common/entities/pa-template.entity';

@Module({
    imports: [TypeOrmModule.forFeature([User, AuditLog, PATemplate])],
    providers: [AdminService],
    controllers: [AdminController],
})
export class AdminModule { }