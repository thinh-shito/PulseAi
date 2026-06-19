import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { TemplatesController } from './templates.controller';
import { PATemplate } from '../common/entities/pa-template.entity';

@Module({
    imports: [TypeOrmModule.forFeature([PATemplate])],
    controllers: [TemplatesController],
})
export class TemplatesModule { }