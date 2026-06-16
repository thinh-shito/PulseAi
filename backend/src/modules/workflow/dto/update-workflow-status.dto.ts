import { IsString, IsNotEmpty, IsEnum, IsOptional } from 'class-validator';
import { WorkflowStatus } from '../../../domain/models/workflow.entity';

export class UpdateWorkflowStatusDto {
  @IsEnum(WorkflowStatus)
  @IsNotEmpty()
  status: WorkflowStatus;

  @IsString()
  @IsOptional()
  notes?: string;
}