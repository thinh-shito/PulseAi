import { IsString, IsNotEmpty, IsOptional, IsUUID } from 'class-validator';

export class CreateWorkflowDto {
  @IsString()
  @IsNotEmpty()
  patient_id: string;

  @IsString()
  @IsNotEmpty()
  patient_name: string;

  @IsString()
  @IsNotEmpty()
  insurance_provider: string;

  @IsString()
  @IsNotEmpty()
  procedure_code: string;

  @IsString()
  @IsNotEmpty()
  diagnosis_code: string;

  @IsString()
  @IsNotEmpty()
  clinical_notes: string;

  @IsUUID()
  @IsOptional()
  template_id?: string;
}