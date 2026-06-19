import { Controller, Post, Body, UseGuards } from '@nestjs/common';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';

class ChatDto {
    message: string;
    workflow_id?: string;
}

@Controller('api/v1/chat')
@UseGuards(JwtAuthGuard)
export class ChatController {
    @Post()
    async chat(@Body() dto: ChatDto) {
        // TODO: proxy to ai-service chat endpoint when streaming is implemented
        return {
            reply: 'Chat feature coming soon.',
            workflow_id: dto.workflow_id ?? null,
        };
    }
}