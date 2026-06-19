import { Controller, Get, Param, UseGuards, Request, Query, NotFoundException, Res } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Response } from 'express';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { RolesGuard } from '../auth/roles.guard';
import { Roles } from '../auth/roles.decorator';
import { UserRole } from '../common/entities/user.entity';
import { PATemplate } from '../common/entities/pa-template.entity';

@Controller('api/v1/templates')
@UseGuards(JwtAuthGuard, RolesGuard)
@Roles(UserRole.DOCTOR, UserRole.ADMIN)
export class TemplatesController {
    constructor(
        @InjectRepository(PATemplate)
        private templateRepository: Repository<PATemplate>,
    ) { }

    @Get()
    async list(@Query('all') all: string, @Request() req) {
        if (all === 'true' && req.user.role === UserRole.ADMIN) {
            return this.templateRepository.find({ order: { created_at: 'DESC' } });
        }
        return this.templateRepository.find({
            where: { is_active: true },
            order: { created_at: 'DESC' },
        });
    }

    @Get(':id/download-blank')
    async downloadBlank(@Param('id') id: string, @Res() res: Response) {
        const template = await this.templateRepository.findOne({ where: { id, is_active: true } });
        if (!template) throw new NotFoundException('Template not found');

        const fileBuffer = Buffer.from(template.file_content, 'base64');
        res.set({
            'Content-Type': 'application/pdf',
            'Content-Disposition': `attachment; filename=blank_${template.name}.pdf`,
        });
        res.send(fileBuffer);
    }
}