import { IsBoolean, IsString, IsOptional } from 'class-validator';

export class UpdateTemplateDto {
  @IsBoolean()
  @IsOptional()
  is_active?: boolean;

  @IsString()
  @IsOptional()
  name?: string;
}