import {
  Controller,
  Get,
  Post,
  Body,
  Query,
  UseGuards,
  ParseIntPipe,
} from '@nestjs/common';
import { AdminService } from './admin.service';
import { CreateUserDto } from './dto/create-user.dto';
import { JwtAuthGuard } from '../../common/guards/jwt-auth.guard';
import { RolesGuard } from '../../core/security/roles.guard';
import { Roles } from '../../common/decorators/roles.decorator';
import { UserRole } from '../../domain/models/user.entity';

@Controller('admin')
@UseGuards(JwtAuthGuard, RolesGuard)
@Roles(UserRole.ADMIN)
export class AdminController {
  constructor(private readonly adminService: AdminService) {}

  @Get('users')
  async listUsers(
    @Query('skip', new ParseIntPipe({ optional: true })) skip?: number,
    @Query('limit', new ParseIntPipe({ optional: true })) limit?: number,
  ) {
    return this.adminService.listUsers(skip, limit);
  }

  @Post('users')
  async createUser(@Body() createUserDto: CreateUserDto) {
    return this.adminService.createUser(createUserDto);
  }

  @Get('audit-logs')
  async listAuditLogs(
    @Query('skip', new ParseIntPipe({ optional: true })) skip?: number,
    @Query('limit', new ParseIntPipe({ optional: true })) limit?: number,
  ) {
    return this.adminService.listAuditLogs(skip, limit);
  }
}