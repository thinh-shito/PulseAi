import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { WorkflowRepository } from '../../infra/repositories/workflow.repository';
import { CreateWorkflowDto } from './dto/create-workflow.dto';
import { UpdateWorkflowStatusDto } from './dto/update-workflow-status.dto';
import { Workflow, WorkflowStatus } from '../../domain/models/workflow.entity';

@Injectable()
export class WorkflowService {
  constructor(private readonly workflowRepository: WorkflowRepository) {}

  async create(createDto: CreateWorkflowDto, userId: string): Promise<Workflow> {
    return this.workflowRepository.create({
      patient_id: createDto.patient_id,
      patient_name: createDto.patient_name,
      insurance_provider: createDto.insurance_provider,
      procedure_code: createDto.procedure_code,
      diagnosis_code: createDto.diagnosis_code,
      clinical_notes: createDto.clinical_notes,
      template_id: createDto.template_id,
      status: WorkflowStatus.DRAFT,
      created_by: userId,
    });
  }

  async findAll(
    skip?: number,
    limit?: number,
    status?: WorkflowStatus,
    patient_id?: string,
  ): Promise<Workflow[]> {
    return this.workflowRepository.findAll({ skip, limit, status, patient_id });
  }

  async findOne(id: string): Promise<Workflow> {
    const workflow = await this.workflowRepository.findById(id);
    if (!workflow) {
      throw new NotFoundException('Workflow not found');
    }
    return workflow;
  }

  async updateStatus(id: string, updateDto: UpdateWorkflowStatusDto): Promise<Workflow> {
    const workflow = await this.findOne(id);

    // Validate state transition rules if necessary
    // E.g., DRAFT -> IN_REVIEW -> APPROVED/REJECTED
    // Let's implement simple check
    if (workflow.status === WorkflowStatus.APPROVED || workflow.status === WorkflowStatus.REJECTED) {
      throw new BadRequestException('Cannot update status of a finalized workflow');
    }

    const updated = await this.workflowRepository.updateStatus(id, updateDto.status);
    if (!updated) {
      throw new NotFoundException('Workflow not found after update');
    }
    return updated;
  }
}