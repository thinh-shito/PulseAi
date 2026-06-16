import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { PATemplate } from '../../domain/models/pa-template.entity';

@Injectable()
export class TemplateRepository {
  constructor(
    @InjectRepository(PATemplate)
    private readonly repository: Repository<PATemplate>,
  ) {}

  async findAll(): Promise<PATemplate[]> {
    return this.repository.find({
      order: { name: 'ASC' },
    });
  }

  async findActive(): Promise<PATemplate[]> {
    return this.repository.find({
      where: { is_active: true },
      order: { name: 'ASC' },
    });
  }

  async findById(id: string): Promise<PATemplate | null> {
    return this.repository.findOne({
      where: { id },
    });
  }

  async findByName(name: string): Promise<PATemplate | null> {
    return this.repository.findOne({
      where: { name },
    });
  }

  async create(templateData: {
    name: string;
    fields: any[];
    file_base64: string;
    is_active?: boolean;
  }): Promise<PATemplate> {
    const template = this.repository.create(templateData);
    return this.repository.save(template);
  }

  async update(
    id: string,
    updates: Partial<PATemplate>,
  ): Promise<PATemplate | null> {
    await this.repository.update(id, updates);
    return this.findById(id);
  }

  async delete(id: string): Promise<boolean> {
    const result = await this.repository.delete(id);
    return (result.affected ?? 0) > 0;
  }

  async count(): Promise<number> {
    return this.repository.count();
  }
}