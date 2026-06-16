import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { TemplatesController } from './templates.controller';
import { TemplatesService } from './templates.service';
import { PATemplate } from '../../domain/models/pa-template.entity';
import { TemplateRepository } from '../../infra/repositories/template.repository';

@Module({
  imports: [
    TypeOrmModule.forFeature([PATemplate]),
  ],
  controllers: [TemplatesController],
  providers: [
    TemplatesService,
    TemplateRepository,
  ],
  exports: [TemplatesService],
})
export class TemplatesModule {}