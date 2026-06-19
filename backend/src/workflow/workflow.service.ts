import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { firstValueFrom } from 'rxjs';
import { Workflow, WorkflowStatus } from '../common/entities/workflow.entity';
import { AuditLog } from '../common/entities/audit-log.entity';

@Injectable()
export class WorkflowService {
    private readonly logger = new Logger(WorkflowService.name);
    private readonly aiServiceUrl: string;
    private readonly internalApiKey: string;

    constructor(
        @InjectRepository(Workflow)
        private workflowRepository: Repository<Workflow>,
        @InjectRepository(AuditLog)
        private auditRepository: Repository<AuditLog>,
        private httpService: HttpService,
        private configService: ConfigService,
    ) {
        this.aiServiceUrl = this.configService.get<string>('AI_SERVICE_URL', 'http://ai-service:8001');
        this.internalApiKey = this.configService.get<string>('INTERNAL_API_KEY', 'internal-secret-change-in-production');
    }

    async startWorkflow(patientId: string, rawText: string, createdBy: string): Promise<Workflow> {
        // Create workflow record in PENDING state
        const workflow = this.workflowRepository.create({
            patient_id: patientId,
            created_by: createdBy,
            status: WorkflowStatus.PENDING,
        });
        await this.workflowRepository.save(workflow);

        // Write audit log
        await this.writeAudit(createdBy, 'START_WORKFLOW', { patientId, workflowId: workflow.id });

        // Dispatch to ai-service asynchronously (fire-and-forget, update DB on completion)
        this.dispatchToAiService(workflow.id, patientId, rawText, createdBy).catch((err) =>
            this.logger.error(`AI dispatch failed for workflow ${workflow.id}: ${err.message}`),
        );

        return workflow;
    }

    private async dispatchToAiService(
        workflowId: string,
        patientId: string,
        rawText: string,
        createdBy: string,
    ): Promise<void> {
        // Mark as processing
        await this.workflowRepository.update(workflowId, { status: WorkflowStatus.PROCESSING });

        try {
            const { data } = await firstValueFrom(
                this.httpService.post(
                    `${this.aiServiceUrl}/api/v1/workflow/process`,
                    { workflow_id: workflowId, patient_id: patientId, raw_text: rawText },
                    { headers: { 'x-internal-api-key': this.internalApiKey } },
                ),
            );

            const finalStatus = this.mapAiStatus(data.processing_status);
            await this.workflowRepository.update(workflowId, {
                status: finalStatus,
                payer_type: data.payer_type ?? null,
                quality_score: data.quality_score ?? null,
                result_data: data.prior_auth_form ?? null,
            });
        } catch (err) {
            this.logger.error(`AI service error for workflow ${workflowId}: ${err.message}`);
            await this.workflowRepository.update(workflowId, { status: WorkflowStatus.FAILED });
        }
    }

    private mapAiStatus(aiStatus: string): WorkflowStatus {
        const map: Record<string, WorkflowStatus> = {
            approved: WorkflowStatus.APPROVED,
            awaiting_approval: WorkflowStatus.AWAITING_APPROVAL,
            completed: WorkflowStatus.COMPLETED,
            failed: WorkflowStatus.FAILED,
        };
        return map[aiStatus] ?? WorkflowStatus.COMPLETED;
    }

    async findAll(userId: string, role: string, skip = 0, limit = 100): Promise<Workflow[]> {
        if (role === 'admin' || role === 'doctor') {
            return this.workflowRepository.find({ skip, take: limit, order: { created_at: 'DESC' } });
        }
        return this.workflowRepository.find({
            where: { created_by: userId },
            skip,
            take: limit,
            order: { created_at: 'DESC' },
        });
    }

    async findOne(id: string): Promise<Workflow> {
        const wf = await this.workflowRepository.findOne({ where: { id } });
        if (!wf) throw new NotFoundException('Workflow not found');
        return wf;
    }

    private async writeAudit(userId: string, action: string, meta: Record<string, any>): Promise<void> {
        const log = this.auditRepository.create({
            user_id: userId,
            action,
            workflow_id: meta.workflowId,
            patient_id: meta.patientId,
            resource_type: 'workflow',
            resource_id: meta.workflowId,
        });
        await this.auditRepository.save(log);
    }
}