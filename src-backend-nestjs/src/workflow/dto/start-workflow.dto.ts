import { IsNotEmpty, IsString } from 'class-validator';

export class StartWorkflowDto {
  @IsString()
  @IsNotEmpty()
  patient_id: string;

  @IsString()
  @IsNotEmpty()
  raw_text: string;
}
