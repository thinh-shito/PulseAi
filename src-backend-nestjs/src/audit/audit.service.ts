import { Injectable } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { PrismaService } from '../database/prisma.service';

@Injectable()
export class AuditService {
  constructor(private prisma: PrismaService) {}

  async log(data: {
    userId: string;
    action: string;
    patientId?: string;
    workflowId?: string;
    resourceType?: string;
    resourceId?: string;
    metadata?: Record<string, unknown>;
    ipAddress?: string;
    userAgent?: string;
  }) {
    // Audit logs are append-only.
    return this.prisma.auditLog.create({
      data: {
        userId: data.userId,
        action: data.action,
        patientId: data.patientId,
        workflowId: data.workflowId,
        resourceType: data.resourceType,
        resourceId: data.resourceId,
        metadata: (data.metadata ?? {}) as Prisma.InputJsonValue,
        ipAddress: data.ipAddress,
        userAgent: data.userAgent,
      },
    });
  }

  async getLogs(userId?: string) {
    return this.prisma.auditLog.findMany({
      where: userId ? { userId } : {},
      orderBy: { createdAt: 'desc' },
    });
  }
}
