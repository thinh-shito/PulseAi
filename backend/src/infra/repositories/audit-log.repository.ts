import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { AuditLog } from '../../domain/models/audit-log.entity';

@Injectable()
export class AuditLogRepository {
  constructor(
    @InjectRepository(AuditLog)
    private readonly repository: Repository<AuditLog>,
  ) {}

  /**
   * Create a new audit log entry (append-only)
   */
  async create(logData: {
    user_id?: string;
    action: string;
    resource_type?: string;
    resource_id?: string;
    details?: Record<string, any>;
    ip_address?: string;
    user_agent?: string;
  }): Promise<AuditLog> {
    const log = this.repository.create(logData);
    return this.repository.save(log);
  }

  /**
   * Find all audit logs with pagination
   */
  async findAll(skip = 0, take = 50): Promise<[AuditLog[], number]> {
    return this.repository.findAndCount({
      relations: ['user'],
      order: { created_at: 'DESC' },
      skip,
      take,
    });
  }

  /**
   * Find logs by user ID
   */
  async findByUserId(user_id: string, skip = 0, take = 50): Promise<[AuditLog[], number]> {
    return this.repository.findAndCount({
      where: { user_id },
      relations: ['user'],
      order: { created_at: 'DESC' },
      skip,
      take,
    });
  }

  /**
   * Find logs by action
   */
  async findByAction(action: string, skip = 0, take = 50): Promise<[AuditLog[], number]> {
    return this.repository.findAndCount({
      where: { action },
      relations: ['user'],
      order: { created_at: 'DESC' },
      skip,
      take,
    });
  }

  /**
   * Find logs by resource
   */
  async findByResource(
    resource_type: string,
    resource_id: string,
    skip = 0,
    take = 50,
  ): Promise<[AuditLog[], number]> {
    return this.repository.findAndCount({
      where: { resource_type, resource_id },
      relations: ['user'],
      order: { created_at: 'DESC' },
      skip,
      take,
    });
  }

  /**
   * Find logs within a date range
   */
  async findByDateRange(
    startDate: Date,
    endDate: Date,
    skip = 0,
    take = 50,
  ): Promise<[AuditLog[], number]> {
    return this.repository
      .createQueryBuilder('audit_log')
      .leftJoinAndSelect('audit_log.user', 'user')
      .where('audit_log.created_at >= :startDate', { startDate })
      .andWhere('audit_log.created_at <= :endDate', { endDate })
      .orderBy('audit_log.created_at', 'DESC')
      .skip(skip)
      .take(take)
      .getManyAndCount();
  }

  /**
   * Count total audit logs
   */
  async count(): Promise<number> {
    return this.repository.count();
  }

  // Note: No update or delete methods - audit logs are append-only for compliance
}