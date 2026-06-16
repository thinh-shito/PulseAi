import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { WorkflowController } from './workflow.controller';
import { WorkflowService } from './workflow.service';
import { Workflow } from '../../domain/models/workflow.entity';
import { WorkflowRepository } from '../../infra/repositories/workflow.repository';

@Module({
  imports: [TypeOrmModule.forFeature([Workflow])],
  controllers: [WorkflowController],
  providers: [WorkflowService, WorkflowRepository],
  exports: [WorkflowService, WorkflowRepository],
})
export class WorkflowModule {}