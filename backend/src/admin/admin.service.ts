import { Injectable, NotFoundException, ConflictException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import * as bcrypt from 'bcryptjs';
import { User, UserRole } from '../common/entities/user.entity';
import { AuditLog } from '../common/entities/audit-log.entity';
import { PATemplate } from '../common/entities/pa-template.entity';

@Injectable()
export class AdminService {
    constructor(
        @InjectRepository(User)
        private userRepository: Repository<User>,
        @InjectRepository(AuditLog)
        private auditRepository: Repository<AuditLog>,
        @InjectRepository(PATemplate)
        private templateRepository: Repository<PATemplate>,
    ) { }

    // ── Users ────────────────────────────────────────────────────────────────

    async listUsers(skip = 0, limit = 100): Promise<User[]> {
        return this.userRepository.find({ skip, take: limit, order: { created_at: 'DESC' } });
    }

    async createUser(email: string, password: string, fullName: string, role: UserRole): Promise<User> {
        const existing = await this.userRepository.findOne({ where: { email } });
        if (existing) throw new ConflictException('Email already registered');

        const user = this.userRepository.create({
            email,
            hashed_password: bcrypt.hashSync(password, 10),
            full_name: fullName,
            role,
            is_active: true,
        });
        return this.userRepository.save(user);
    }

    // ── Audit Logs ──────────────────────────────────────────────────────────

    async listAuditLogs(skip = 0, limit = 100): Promise<AuditLog[]> {
        return this.auditRepository.find({ skip, take: limit, order: { created_at: 'DESC' } });
    }

    // ── Templates ───────────────────────────────────────────────────────────

    async createTemplate(
        name: string,
        fields: any[],
        fileContentBase64: string,
        adminUserId: string,
    ): Promise<PATemplate> {
        const template = this.templateRepository.create({
            name,
            fields,
            file_content: fileContentBase64,
            is_active: true,
        });
        const saved = await this.templateRepository.save(template);

        // Audit log — append only
        await this.auditRepository.save(
            this.auditRepository.create({
                user_id: adminUserId,
                action: 'CREATE_TEMPLATE',
                resource_type: 'template',
                resource_id: saved.id,
            }),
        );

        return saved;
    }

    async patchTemplate(
        id: string,
        patch: { is_active?: boolean; name?: string },
        adminUserId: string,
    ): Promise<PATemplate> {
        const template = await this.templateRepository.findOne({ where: { id } });
        if (!template) throw new NotFoundException('Template not found');

        if (patch.is_active !== undefined) template.is_active = patch.is_active;
        if (patch.name !== undefined) template.name = patch.name;

        const saved = await this.templateRepository.save(template);

        await this.auditRepository.save(
            this.auditRepository.create({
                user_id: adminUserId,
                action: 'UPDATE_TEMPLATE',
                resource_type: 'template',
                resource_id: saved.id,
            }),
        );

        return saved;
    }
}