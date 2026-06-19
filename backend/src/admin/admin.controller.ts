import {
    Controller, Get, Post, Patch, Body, Param,
    UseGuards, Request, Query, HttpCode, HttpStatus,
    UploadedFile, UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { AdminService } from './admin.service';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { RolesGuard } from '../auth/roles.guard';
import { Roles } from '../auth/roles.decorator';
import { UserRole } from '../common/entities/user.entity';

class CreateUserDto {
    email: string;
    password: string;
    full_name: string;
    role: UserRole;
}

class PatchTemplateDto {
    is_active?: boolean;
    name?: string;
}

@Controller('api/v1/admin')
@UseGuards(JwtAuthGuard, RolesGuard)
@Roles(UserRole.ADMIN)
export class AdminController {
    constructor(private adminService: AdminService) { }

    // ── Users ──────────────────────────────────────────────────────────────

    @Get('users')
    async listUsers(@Query('skip') skip = '0', @Query('limit') limit = '100') {
        return this.adminService.listUsers(+skip, +limit);
    }

    @Post('users')
    @HttpCode(HttpStatus.CREATED)
    async createUser(@Body() dto: CreateUserDto) {
        return this.adminService.createUser(dto.email, dto.password, dto.full_name, dto.role);
    }

    // ── Audit Logs ─────────────────────────────────────────────────────────

    @Get('audit-logs')
    async listAuditLogs(@Query('skip') skip = '0', @Query('limit') limit = '100') {
        return this.adminService.listAuditLogs(+skip, +limit);
    }

    // ── Templates ──────────────────────────────────────────────────────────

    @Post('templates')
    @HttpCode(HttpStatus.CREATED)
    @UseInterceptors(FileInterceptor('file'))
    async createTemplate(
        @UploadedFile() file: any,
        @Body('schema_data') schemaData: string,
        @Request() req,
    ) {
        const schema = JSON.parse(schemaData);
        const fileContentBase64 = file.buffer.toString('base64');
        return this.adminService.createTemplate(
            schema.name ?? file.originalname,
            schema.fields ?? [],
            fileContentBase64,
            req.user.id,
        );
    }

    @Patch('templates/:id')
    async patchTemplate(
        @Param('id') id: string,
        @Body() dto: PatchTemplateDto,
        @Request() req,
    ) {
        return this.adminService.patchTemplate(id, dto, req.user.id);
    }
}