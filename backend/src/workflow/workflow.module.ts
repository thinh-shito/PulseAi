import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { HttpModule } from '@nestjs/axios';
import { WorkflowService } from './workflow.service';
import { WorkflowController } from './workflow.controller';
import { Workflow } from '../common/entities/workflow.entity';
import { AuditLog } from '../common/entities/audit-log.entity';

@Module({
    imports: [
        TypeOrmModule.forFeature([Workflow, AuditLog]),
        HttpModule,
    ],
    providers: [WorkflowService],
    controllers: [WorkflowController],
    exports: [WorkflowService],
})
export class WorkflowModule { }