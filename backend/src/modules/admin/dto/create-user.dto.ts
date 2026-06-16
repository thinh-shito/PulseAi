import { IsString, IsNotEmpty, IsEmail, IsEnum, MinLength } from 'class-validator';
import { UserRole } from '../../../domain/models/user.entity';

export class CreateUserDto {
  @IsEmail()
  @IsNotEmpty()
  email: string;

  @IsString()
  @MinLength(8)
  password: string;

  @IsString()
  @IsNotEmpty()
  full_name: string;

  @IsEnum(UserRole)
  role: UserRole;
}