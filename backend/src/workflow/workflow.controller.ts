import { Controller, Post, Get, Param, Body, UseGuards, Request, Query } from '@nestjs/common';
import { WorkflowService } from './workflow.service';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';

class StartWorkflowDto {
    patient_id: string;
    raw_text: string;
}

@Controller('api/v1/workflow')
@UseGuards(JwtAuthGuard)
export class WorkflowController {
    constructor(private workflowService: WorkflowService) { }

    @Post('start')
    async start(@Body() dto: StartWorkflowDto, @Request() req) {
        return this.workflowService.startWorkflow(dto.patient_id, dto.raw_text, req.user.id);
    }

    @Get()
    async list(@Request() req, @Query('skip') skip = '0', @Query('limit') limit = '100') {
        return this.workflowService.findAll(req.user.id, req.user.role, +skip, +limit);
    }

    @Get(':id')
    async getOne(@Param('id') id: string) {
        return this.workflowService.findOne(id);
    }
}