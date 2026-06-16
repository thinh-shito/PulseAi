import {
  Controller,
  Get,
  Post,
  Patch,
  Body,
  Param,
  Query,
  UseGuards,
  ParseUUIDPipe,
  ParseIntPipe,
} from '@nestjs/common';
import { WorkflowService } from './workflow.service';
import { CreateWorkflowDto } from './dto/create-workflow.dto';
import { UpdateWorkflowStatusDto } from './dto/update-workflow-status.dto';
import { JwtAuthGuard } from '../../common/guards/jwt-auth.guard';
import { RolesGuard } from '../../core/security/roles.guard';
import { Roles } from '../../common/decorators/roles.decorator';
import { CurrentUser } from '../../common/decorators/user.decorator';
import { UserRole } from '../../domain/models/user.entity';
import { WorkflowStatus } from '../../domain/models/workflow.entity';

@Controller('workflow')
@UseGuards(JwtAuthGuard, RolesGuard)
export class WorkflowController {
  constructor(private readonly workflowService: WorkflowService) {}

  @Post()
  @Roles(UserRole.DOCTOR, UserRole.ADMIN)
  async create(@Body() createDto: CreateWorkflowDto, @CurrentUser() user: any) {
    return this.workflowService.create(createDto, user.userId);
  }

  @Get()
  async findAll(
    @Query('skip', new ParseIntPipe({ optional: true })) skip?: number,
    @Query('limit', new ParseIntPipe({ optional: true })) limit?: number,
    @Query('status') status?: WorkflowStatus,
    @Query('patient_id') patient_id?: string,
  ) {
    return this.workflowService.findAll(skip, limit, status, patient_id);
  }

  @Get(':id')
  async findOne(@Param('id', ParseUUIDPipe) id: string) {
    return this.workflowService.findOne(id);
  }

  @Patch(':id/status')
  @Roles(UserRole.DOCTOR, UserRole.ADMIN)
  async updateStatus(
    @Param('id', ParseUUIDPipe) id: string,
    @Body() updateDto: UpdateWorkflowStatusDto,
  ) {
    return this.workflowService.updateStatus(id, updateDto);
  }
}