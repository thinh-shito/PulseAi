import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AuthModule } from './auth/auth.module';
import { WorkflowModule } from './workflow/workflow.module';
import { AdminModule } from './admin/admin.module';
import { TemplatesModule } from './templates/templates.module';
import { HealthController } from './health/health.controller';
import { ChatController } from './chat/chat.controller';
import { User } from './common/entities/user.entity';
import { Workflow } from './common/entities/workflow.entity';
import { AuditLog } from './common/entities/audit-log.entity';
import { PATemplate } from './common/entities/pa-template.entity';

@Module({
    imports: [
        ConfigModule.forRoot({ isGlobal: true }),
        TypeOrmModule.forRootAsync({
            imports: [ConfigModule],
            inject: [ConfigService],
            useFactory: (config: ConfigService) => ({
                type: 'postgres',
                url: config.get<string>('DATABASE_URL', 'postgresql://pulseai:pulseai_secret@postgres:5432/pulseai_db'),
                entities: [User, Workflow, AuditLog, PATemplate],
                synchronize: config.get<string>('NODE_ENV') !== 'production',
                logging: config.get<string>('NODE_ENV') === 'development',
            }),
        }),
        AuthModule,
        WorkflowModule,
        AdminModule,
        TemplatesModule,
    ],
    controllers: [HealthController, ChatController],
})
export class AppModule { }