import {
  Controller,
  Post,
  Get,
  Patch,
  Param,
  Body,
  Req,
  UseGuards,
  Sse,
  Res,
  BadRequestException,
} from '@nestjs/common';
import { WorkflowService } from './workflow.service';
import { StartWorkflowDto } from './dto/start-workflow.dto';
import { UpdateFieldsDto } from './dto/update-fields.dto';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { RolesGuard } from '../auth/roles.guard';
import { Roles } from '../auth/roles.decorator';
import { Role } from '@prisma/client';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import type { FastifyRequest, FastifyReply } from 'fastify';

interface AuthUser {
  id: string;
  role: Role;
}

interface AuthenticatedRequest extends FastifyRequest {
  user: AuthUser;
}

@UseGuards(JwtAuthGuard, RolesGuard)
@Controller('workflow')
export class WorkflowController {
  constructor(private workflowService: WorkflowService) {}

  @Post('start')
  start(@Body() dto: StartWorkflowDto, @Req() req: AuthenticatedRequest) {
    return this.workflowService.start(
      dto.patient_id,
      dto.raw_text,
      req.user.id,
    );
  }

  @Get()
  list(@Req() req: AuthenticatedRequest) {
    return this.workflowService.list(req.user.id, req.user.role);
  }

  @Get(':id')
  get(@Param('id') id: string) {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!id || !uuidRegex.test(id)) {
      throw new BadRequestException('Invalid workflow ID format');
    }
    return this.workflowService.get(id);
  }

  @Sse(':id/stream')
  stream(@Param('id') id: string): Observable<{ data: unknown }> {
    return this.workflowService
      .getStream(id)
      .pipe(map((event) => ({ data: event })));
  }

  @Roles(Role.doctor, Role.admin)
  @Post(':id/approve')
  approve(@Param('id') id: string, @Req() req: AuthenticatedRequest) {
    return this.workflowService.approve(id, req.user.id);
  }

  @Roles(Role.doctor, Role.admin)
  @Post(':id/reject')
  reject(@Param('id') id: string, @Req() req: AuthenticatedRequest) {
    return this.workflowService.reject(id, req.user.id);
  }

  @Patch(':id/fields')
  updateFields(
    @Param('id') id: string,
    @Body() dto: UpdateFieldsDto,
    @Req() req: AuthenticatedRequest,
  ) {
    return this.workflowService.updateFields(id, dto.fields, req.user.id);
  }

  @Get(':id/export-pdf')
  async exportPdf(
    @Param('id') id: string,
    @Req() req: AuthenticatedRequest,
    @Res() res: FastifyReply,
  ) {
    const buffer = await this.workflowService.exportPdf(id, req.user.id);
    return res
      .headers({
        'Content-Type': 'application/pdf',
        'Content-Disposition': `attachment; filename=prior_auth_${id}.pdf`,
        'Content-Length': buffer.length,
      })
      .send(buffer);
  }

  @Post('upload-document')
  async uploadDocument(@Req() req: AuthenticatedRequest) {
    const multipart = req as unknown as {
      file(): Promise<
        { filename: string; toBuffer(): Promise<Buffer> } | undefined
      >;
    };
    const file = await multipart.file();
    if (!file) {
      throw new BadRequestException('No file uploaded');
    }
    const buffer = await file.toBuffer();
    return this.workflowService.extractText(file.filename, buffer);
  }
}
