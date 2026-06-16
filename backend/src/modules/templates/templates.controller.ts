import {
  Controller,
  Get,
  Post,
  Patch,
  Param,
  Query,
  Body,
  UseGuards,
  UseInterceptors,
  UploadedFile,
  BadRequestException,
  Res,
  ParseBoolPipe,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { Response } from 'express';
import { TemplatesService } from './templates.service';
import { UpdateTemplateDto } from './dto/update-template.dto';
import { JwtAuthGuard } from '../../common/guards/jwt-auth.guard';
import { RolesGuard } from '../../core/security/roles.guard';
import { Roles } from '../../common/decorators/roles.decorator';
import { CurrentUser } from '../../common/decorators/user.decorator';
import { UserRole } from '../../domain/models/user.entity';

@Controller()
@UseGuards(JwtAuthGuard, RolesGuard)
export class TemplatesController {
  constructor(private readonly templatesService: TemplatesService) {}

  // Public templates endpoint (DOCTOR, ADMIN)
  @Get('templates')
  @Roles(UserRole.DOCTOR, UserRole.ADMIN)
  async listTemplates(
    @Query('all', new ParseBoolPipe({ optional: true })) all?: boolean,
    @CurrentUser() user?: any,
  ) {
    return this.templatesService.listTemplates(all || false, user?.role);
  }

  @Get('templates/:id/download-blank')
  @Roles(UserRole.DOCTOR, UserRole.ADMIN)
  async downloadBlankTemplate(@Param('id') id: string, @Res() res: Response) {
    const template = await this.templatesService.getTemplateById(id);
    const fileBuffer = await this.templatesService.getTemplateFile(id);

    res.set({
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename=blank_${template.name}.pdf`,
      'Content-Length': fileBuffer.length,
    });

    res.send(fileBuffer);
  }

  // Admin-only endpoints
  @Post('admin/templates')
  @Roles(UserRole.ADMIN)
  @UseInterceptors(FileInterceptor('file'))
  async createTemplate(
    @UploadedFile() file: any,
    @Body('schema_data') schemaData: string,
  ) {
    if (!file) {
      throw new BadRequestException('File is required');
    }

    if (file.mimetype !== 'application/pdf') {
      throw new BadRequestException('File must be PDF format');
    }

    let parsedSchema: { name: string; fields: any[] };
    try {
      parsedSchema = JSON.parse(schemaData);
    } catch {
      throw new BadRequestException('Invalid JSON schema');
    }

    if (!parsedSchema.name || !parsedSchema.fields) {
      throw new BadRequestException('Schema must include name and fields');
    }

    return this.templatesService.createTemplate(
      parsedSchema.name,
      parsedSchema.fields,
      file.buffer,
    );
  }

  @Patch('admin/templates/:id')
  @Roles(UserRole.ADMIN)
  async updateTemplate(
    @Param('id') id: string,
    @Body() updateDto: UpdateTemplateDto,
  ) {
    return this.templatesService.updateTemplate(id, updateDto);
  }
}