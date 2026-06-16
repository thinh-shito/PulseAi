import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { AuditLogRepository } from '../../infra/repositories/audit-log.repository';
import { PHIFilterService } from '../../domain/phi-filter/phi-filter.service';

@Injectable()
export class AuditInterceptor implements NestInterceptor {
  constructor(
    private readonly auditLogRepository: AuditLogRepository,
    private readonly phiFilterService: PHIFilterService,
  ) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const request = context.switchToHttp().getRequest();
    const { method, url, user, ip, headers } = request;

    // Only audit state-changing operations (POST, PUT, DELETE, PATCH)
    const isStateChanging = ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method);
    if (!isStateChanging) {
      return next.handle();
    }

    // Skip auth/login body to avoid logging passwords
    const isLogin = url.includes('/auth/login') || url.includes('/auth/register');

    const details = {
      method,
      url,
      body: isLogin ? { username: request.body?.username } : this.phiFilterService.sanitizeMetadata(request.body || {}),
      params: request.params,
      query: request.query,
    };

    return next.handle().pipe(
      tap({
        next: (data) => {
          const action = `${method} ${url}`;
          const resourceType = this.determineResourceType(url);
          const resourceId = data?.workflow_id || data?.user_id || data?.template_id || request.params?.id || null;

          this.auditLogRepository.create({
            user_id: user?.user_id || null,
            action,
            resource_type: resourceType,
            resource_id: resourceId,
            details,
            ip_address: ip || request.headers['x-forwarded-for'] || null,
            user_agent: headers['user-agent'] || null,
          }).catch((err) => {
            console.error('Failed to create audit log:', err);
          });
        },
        error: (err) => {
          const action = `${method} ${url} (FAILED)`;
          this.auditLogRepository.create({
            user_id: user?.user_id || null,
            action,
            details: {
              ...details,
              error: err.message,
            },
            ip_address: ip || request.headers['x-forwarded-for'] || null,
            user_agent: headers['user-agent'] || null,
          }).catch((loggingError) => {
            console.error('Failed to create failed audit log:', loggingError);
          });
        },
      }),
    );
  }

  private determineResourceType(url: string): string {
    if (url.includes('/auth')) return 'AUTH';
    if (url.includes('/users') || url.includes('/user')) return 'USER';
    if (url.includes('/workflows') || url.includes('/workflow')) return 'WORKFLOW';
    if (url.includes('/admin')) return 'ADMIN';
    if (url.includes('/templates') || url.includes('/template')) return 'TEMPLATE';
    if (url.includes('/presence')) return 'PRESENCE';
    if (url.includes('/chat')) return 'CHAT';
    return 'UNKNOWN';
  }
}