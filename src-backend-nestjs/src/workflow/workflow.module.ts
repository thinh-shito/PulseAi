import { Module } from '@nestjs/common';
import { ClientsModule, Transport } from '@nestjs/microservices';
import { join } from 'path';
import { WorkflowService } from './workflow.service';
import { WorkflowController } from './workflow.controller';

@Module({
  imports: [
    ClientsModule.registerAsync([
      {
        name: 'AI_PACKAGE',
        useFactory: () => ({
          transport: Transport.GRPC,
          options: {
            package: 'ai',
            protoPath: join(process.cwd(), '../protos/ai_service.proto'),
            url: process.env.AI_SERVICE_URL || 'localhost:50051',
            loader: {
              keepCase: true,
            },
          },
        }),
      },
    ]),
  ],
  controllers: [WorkflowController],
  providers: [WorkflowService],
  exports: [WorkflowService],
})
export class WorkflowModule {}
