import {
  Injectable,
  Inject,
  OnModuleInit,
  NotFoundException,
  BadRequestException,
} from '@nestjs/common';
import * as microservices from '@nestjs/microservices';
import { Prisma } from '@prisma/client';
import { PrismaService } from '../database/prisma.service';
import { AuditService } from '../audit/audit.service';
import { Observable, Subject } from 'rxjs';
import { WorkflowStatus, Role } from '@prisma/client';

// ─── gRPC interface contracts (mirror ai_service.proto) ─────────────────────

export interface AnonymizeRequest {
  raw_text: string;
  patient_id: string;
}

export interface AnonymizeResponse {
  anonymized_text: string;
}

export interface StartWorkflowRequest {
  patient_id: string;
  anonymized_text: string;
  workflow_id: string;
}

export interface WorkflowEvent {
  node_name: string;
  status: string;
  icd10_codes: string[];
  confidence_score: number;
  payer_type: string;
  quality_score: number;
  state_json: string;
  error_message: string;
  retry_count: number;
}

export interface ExportPdfRequest {
  workflow_id: string;
  status: string;
  payer_type: string;
  quality_score: number;
  patient_id: string;
  fields_json: string;
  template_file_content_base64?: string;
  template_fields_json?: string;
}

export interface ExportPdfResponse {
  pdf_bytes: Uint8Array;
}

export interface ExtractTextRequest {
  file_name: string;
  file_bytes: Uint8Array;
}

export interface ExtractTextResponse {
  extracted_text: string;
}

export interface AiServiceClient {
  anonymizeText(request: AnonymizeRequest): Observable<AnonymizeResponse>;
  startWorkflow(request: StartWorkflowRequest): Observable<WorkflowEvent>;
  exportPdf(request: ExportPdfRequest): Observable<ExportPdfResponse>;
  extractText(request: ExtractTextRequest): Observable<ExtractTextResponse>;
}

// ─── Typed shape of prior_auth_form / AgentState JSON ──────────────────────

interface PriorAuthForm {
  fields?: Record<string, string | null>;
  [key: string]: unknown;
}

interface AgentState {
  summary?: string;
  prior_auth_form?: PriorAuthForm;
  [key: string]: unknown;
}

// ─── Service ─────────────────────────────────────────────────────────────────

@Injectable()
export class WorkflowService implements OnModuleInit {
  private aiServiceClient!: AiServiceClient;
  private activeStreams = new Map<string, Subject<unknown>>();

  constructor(
    private prisma: PrismaService,
    private auditService: AuditService,
    @Inject('AI_PACKAGE') private client: microservices.ClientGrpc,
  ) {}

  onModuleInit() {
    this.aiServiceClient = this.client.getService<AiServiceClient>('AiService');
  }

  async start(patientId: string, rawText: string, userId: string) {
    const workflow = await this.prisma.workflow.create({
      data: {
        patientId,
        createdBy: userId,
        status: WorkflowStatus.pending,
      },
    });

    const workflowId = workflow.id;
    const subject = new Subject<unknown>();
    this.activeStreams.set(workflowId, subject);

    await this.auditService.log({
      userId,
      action: 'START_WORKFLOW',
      patientId,
      workflowId,
      resourceType: 'workflow',
      resourceId: workflowId,
    });

    void this.runBackgroundPipeline(
      workflowId,
      patientId,
      rawText,
      userId,
      subject,
    );

    return workflow;
  }

  private async runBackgroundPipeline(
    workflowId: string,
    patientId: string,
    rawText: string,
    userId: string,
    subject: Subject<unknown>,
  ): Promise<void> {
    try {
      subject.next({
        status: 'processing',
        message: 'Anonymizing clinical records...',
      });

      const anonymizeRes = await this.aiServiceClient
        .anonymizeText({ raw_text: rawText, patient_id: patientId })
        .toPromise();

      if (!anonymizeRes) {
        throw new Error('Anonymization service failed to return response');
      }

      const anonymizedText = anonymizeRes.anonymized_text;

      await this.prisma.workflow.update({
        where: { id: workflowId },
        data: { status: WorkflowStatus.processing },
      });

      const stream = this.aiServiceClient.startWorkflow({
        patient_id: patientId,
        anonymized_text: anonymizedText,
        workflow_id: workflowId,
      });

      stream.subscribe({
        next: (event: WorkflowEvent) => {
          void this.handleWorkflowEvent(event, workflowId, patientId, subject);
        },
        error: (err: Error) => {
          void (async () => {
            console.error('Workflow gRPC stream error:', err);
            await this.prisma.workflow.update({
              where: { id: workflowId },
              data: { status: WorkflowStatus.failed },
            });
            subject.next({ status: 'failed', error: err.message });
            subject.complete();
            this.activeStreams.delete(workflowId);
          })();
        },
        complete: () => {
          subject.next({ status: 'completed' });
          subject.complete();
          this.activeStreams.delete(workflowId);
        },
      });
    } catch (error: unknown) {
      console.error('Error starting workflow:', error);
      const message = error instanceof Error ? error.message : 'Unknown error';
      await this.prisma.workflow.update({
        where: { id: workflowId },
        data: { status: WorkflowStatus.failed },
      });
      subject.next({ status: 'failed', error: message });
      subject.complete();
      this.activeStreams.delete(workflowId);
    }
  }

  private async handleWorkflowEvent(
    event: WorkflowEvent,
    workflowId: string,
    patientId: string,
    subject: Subject<unknown>,
  ): Promise<void> {
    try {
      const parsedState: AgentState = event.state_json
        ? (JSON.parse(event.state_json) as AgentState)
        : {};

      const statusMap: Record<string, WorkflowStatus> = {
        pending: WorkflowStatus.pending,
        extracting: WorkflowStatus.processing,
        routing: WorkflowStatus.processing,
        filling_form: WorkflowStatus.processing,
        quality_check: WorkflowStatus.processing,
        awaiting_approval: WorkflowStatus.awaiting_approval,
        approved: WorkflowStatus.approved,
        rejected: WorkflowStatus.rejected,
        completed: WorkflowStatus.completed,
        failed: WorkflowStatus.failed,
      };

      const mappedStatus: WorkflowStatus =
        statusMap[event.status] ?? WorkflowStatus.processing;

      const updateData: Record<string, unknown> = { status: mappedStatus };
      if (event.payer_type) updateData.payerType = event.payer_type;
      if (event.quality_score) updateData.qualityScore = event.quality_score;
      if (parsedState.prior_auth_form) {
        updateData.resultData = parsedState.prior_auth_form;
      }

      await this.prisma.workflow.update({
        where: { id: workflowId },
        data: updateData,
      });

      if (
        ['completed', 'approved', 'awaiting_approval'].includes(event.status)
      ) {
        const existingRecord = await this.prisma.clinicalRecord.findFirst({
          where: { workflowId },
        });
        if (!existingRecord) {
          await this.prisma.clinicalRecord.create({
            data: {
              workflowId,
              patientId,
              icd10Codes: event.icd10_codes ?? [],
              summary: parsedState.summary ?? '',
              confidenceScore: event.confidence_score ?? 0.0,
            },
          });
        }
      }

      subject.next({
        status: mappedStatus,
        payer_type: event.payer_type || null,
        quality_score: event.quality_score || null,
        prior_auth_form: parsedState.prior_auth_form ?? null,
        icd10_codes: event.icd10_codes ?? null,
        summary: parsedState.summary ?? null,
      });
    } catch (err) {
      console.error('Error handling workflow stream update:', err);
    }
  }

  getStream(workflowId: string): Observable<unknown> {
    const subject = this.activeStreams.get(workflowId);
    if (!subject) {
      const fallback = new Subject<unknown>();
      setTimeout(() => {
        fallback.next({
          status: 'completed',
          message: 'Workflow is already complete',
        });
        fallback.complete();
      }, 0);
      return fallback.asObservable();
    }
    return subject.asObservable();
  }

  async list(userId: string, role: Role) {
    if (role === Role.admin || role === Role.doctor) {
      return this.prisma.workflow.findMany({ orderBy: { createdAt: 'desc' } });
    }
    return this.prisma.workflow.findMany({
      where: { createdBy: userId },
      orderBy: { createdAt: 'desc' },
    });
  }

  async get(id: string) {
    const wf = await this.prisma.workflow.findUnique({
      where: { id },
      include: { clinicalRecords: true },
    });
    if (!wf) throw new NotFoundException('Workflow not found');
    return wf;
  }

  async approve(id: string, userId: string) {
    const wf = await this.get(id);
    if (wf.status !== WorkflowStatus.awaiting_approval) {
      throw new BadRequestException(
        'Workflow is not in awaiting_approval state',
      );
    }

    const updated = await this.prisma.workflow.update({
      where: { id },
      data: { status: WorkflowStatus.approved },
    });

    await this.auditService.log({
      userId,
      action: 'APPROVE_WORKFLOW',
      patientId: wf.patientId,
      workflowId: id,
      resourceType: 'workflow',
      resourceId: id,
    });

    return updated;
  }

  async reject(id: string, userId: string) {
    const wf = await this.get(id);
    if (wf.status !== WorkflowStatus.awaiting_approval) {
      throw new BadRequestException(
        'Workflow is not in awaiting_approval state',
      );
    }

    const updated = await this.prisma.workflow.update({
      where: { id },
      data: { status: WorkflowStatus.rejected },
    });

    await this.auditService.log({
      userId,
      action: 'REJECT_WORKFLOW',
      patientId: wf.patientId,
      workflowId: id,
      resourceType: 'workflow',
      resourceId: id,
    });

    return updated;
  }

  async updateFields(
    id: string,
    fields: Record<string, string>,
    userId: string,
  ) {
    const wf = await this.get(id);
    if (!wf.resultData) {
      throw new BadRequestException('Workflow does not have result data');
    }

    const resultDataObj = wf.resultData as PriorAuthForm;
    if (!resultDataObj.fields) {
      resultDataObj.fields = {};
    }

    for (const [key, val] of Object.entries(fields)) {
      resultDataObj.fields[key] = val;
    }

    // Recalculate quality score
    const clinicalRecord = await this.prisma.clinicalRecord.findFirst({
      where: { workflowId: id },
    });
    const confidence = clinicalRecord?.confidenceScore ?? 1.0;

    let deductions = 0;
    for (const val of Object.values(resultDataObj.fields)) {
      const strVal = val === null ? '' : String(val).trim();
      if (strVal === '' || strVal.toUpperCase() === 'N/A') {
        deductions += 15;
      }
    }

    const qualityScore = Math.max(
      0.0,
      Math.min(100.0, confidence * 100.0 - deductions),
    );

    const updated = await this.prisma.workflow.update({
      where: { id },
      data: {
        resultData: resultDataObj as unknown as Prisma.InputJsonValue,
        qualityScore,
      },
    });

    await this.auditService.log({
      userId,
      action: 'EDIT_FIELDS',
      patientId: wf.patientId,
      workflowId: id,
      resourceType: 'workflow',
      resourceId: id,
    });

    return updated;
  }

  async exportPdf(id: string, userId: string): Promise<Buffer> {
    const wf = await this.get(id);
    if (!wf.resultData) {
      throw new BadRequestException('Workflow does not have result data');
    }

    const resultDataObj = wf.resultData as PriorAuthForm;
    const fields: Record<string, string | null> = resultDataObj.fields ?? {};

    await this.auditService.log({
      userId,
      action: 'EXPORT_PDF',
      patientId: wf.patientId,
      workflowId: id,
      resourceType: 'workflow',
      resourceId: id,
    });

    let templateBytesBase64 = '';
    let templateFieldsJson = '';

    if (wf.payerType) {
      const template = await this.prisma.pATemplate.findFirst({
        where: {
          isActive: true,
          name: { contains: wf.payerType, mode: 'insensitive' },
        },
      });

      if (template) {
        templateBytesBase64 = template.fileContent ?? '';
        templateFieldsJson = JSON.stringify(template.fields);
      }
    }

    const res = await this.aiServiceClient
      .exportPdf({
        workflow_id: id,
        status: wf.status,
        payer_type: wf.payerType ?? '',
        quality_score: wf.qualityScore ?? 0.0,
        patient_id: wf.patientId,
        fields_json: JSON.stringify(fields),
        template_file_content_base64: templateBytesBase64,
        template_fields_json: templateFieldsJson,
      })
      .toPromise();

    if (!res?.pdf_bytes) {
      throw new Error('Failed to generate PDF from AI service');
    }

    return Buffer.from(res.pdf_bytes);
  }

  async extractText(fileName: string, fileBytes: Buffer) {
    const res = await this.aiServiceClient
      .extractText({
        file_name: fileName,
        file_bytes: new Uint8Array(fileBytes),
      })
      .toPromise();

    if (!res) throw new Error('Failed to extract text from file');

    return { text: res.extracted_text };
  }
}
