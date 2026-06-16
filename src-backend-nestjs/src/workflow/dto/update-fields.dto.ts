import { IsNotEmpty, IsObject } from 'class-validator';

export class UpdateFieldsDto {
  @IsObject()
  @IsNotEmpty()
  fields: Record<string, string>;
}
