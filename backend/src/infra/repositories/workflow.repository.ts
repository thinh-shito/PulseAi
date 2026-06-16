import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Workflow, WorkflowStatus } from '../../domain/models/workflow.entity';

@Injectable()
export class WorkflowRepository {
  constructor(
    @InjectRepository(Workflow)
    private readonly repository: Repository<Workflow>,
  ) {}

  async findAll(options?: {
    skip?: number;
    limit?: number;
    status?: WorkflowStatus;
    patient_id?: string;
  }): Promise<Workflow[]> {
    const where: any = {};
    if (options?.status) where.status = options.status;
    if (options?.patient_id) where.patient_id = options.patient_id;

    return this.repository.find({
      where,
      relations: ['user'],
      order: { created_at: 'DESC' },
      skip: options?.skip || 0,
      take: options?.limit || 100,
    });
  }

  async findById(id: string): Promise<Workflow | null> {
    return this.repository.findOne({
      where: { id },
      relations: ['user'],
    });
  }

  async findByUserId(created_by: string): Promise<Workflow[]> {
    return this.repository.find({
      where: { created_by },
      relations: ['user'],
      order: { created_at: 'DESC' },
    });
  }

  async findByStatus(status: WorkflowStatus): Promise<Workflow[]> {
    return this.repository.find({
      where: { status },
      relations: ['user'],
      order: { created_at: 'DESC' },
    });
  }

  async create(workflowData: {
    patient_id: string;
    patient_name: string;
    insurance_provider: string;
    procedure_code: string;
    diagnosis_code: string;
    clinical_notes: string;
    template_id?: string;
    status: WorkflowStatus;
    created_by: string;
  }): Promise<Workflow> {
    const workflow = this.repository.create(workflowData);
    return this.repository.save(workflow);
  }

  async update(
    id: string,
    updates: Partial<Workflow>,
  ): Promise<Workflow | null> {
    await this.repository.update(id, updates);
    return this.findById(id);
  }

  async updateStatus(
    id: string,
    status: WorkflowStatus,
  ): Promise<Workflow | null> {
    return this.update(id, { status });
  }

  async delete(id: string): Promise<boolean> {
    const result = await this.repository.delete(id);
    return (result.affected ?? 0) > 0;
  }

  async count(): Promise<number> {
    return this.repository.count();
  }

  async countByStatus(status: WorkflowStatus): Promise<number> {
    return this.repository.count({ where: { status } });
  }
}