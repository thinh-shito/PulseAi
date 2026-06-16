import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { TemplateRepository } from '../../infra/repositories/template.repository';
import { UpdateTemplateDto } from './dto/update-template.dto';
import { PATemplate } from '../../domain/models/pa-template.entity';

@Injectable()
export class TemplatesService {
  constructor(
    private readonly templateRepository: TemplateRepository,
  ) {}

  async listTemplates(includeAll: boolean, userRole: string): Promise<PATemplate[]> {
    if (includeAll && userRole === 'ADMIN') {
      return this.templateRepository.findAll();
    }
    return this.templateRepository.findActive();
  }

  async getTemplateById(id: string): Promise<PATemplate> {
    const template = await this.templateRepository.findById(id);
    if (!template) {
      throw new NotFoundException('Template not found');
    }
    return template;
  }

  async createTemplate(
    name: string,
    fields: any[],
    fileBuffer: Buffer,
  ): Promise<PATemplate> {
    const base64File = fileBuffer.toString('base64');
    return this.templateRepository.create({
      name,
      fields,
      file_base64: base64File,
      is_active: true,
    });
  }

  async updateTemplate(id: string, updateDto: UpdateTemplateDto): Promise<PATemplate> {
    const template = await this.getTemplateById(id);
    
    const updated = await this.templateRepository.update(id, {
      ...updateDto,
    });

    if (!updated) {
      throw new NotFoundException('Template not found after update');
    }
    return updated;
  }

  async getTemplateFile(id: string): Promise<Buffer> {
    const template = await this.getTemplateById(id);
    if (!template.file_base64) {
      throw new BadRequestException('Template file not available');
    }
    return Buffer.from(template.file_base64, 'base64');
  }
}