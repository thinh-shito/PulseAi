import { Controller, Get } from '@nestjs/common';

@Controller()
export class HealthController {
    @Get('health')
    check() {
        return { status: 'ok', service: 'backend' };
    }

    @Get('api/v1/health')
    checkV1() {
        return { status: 'ok', service: 'backend', version: 'v1' };
    }
}