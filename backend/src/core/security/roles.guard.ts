import {
  Injectable,
  CanActivate,
  ExecutionContext,
  ForbiddenException,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { ROLES_KEY } from '../../common/decorators/roles.decorator';

export enum UserRole {
  ADMIN = 'ADMIN',
  DOCTOR = 'DOCTOR',
  VIEWER = 'VIEWER',
}

// Role hierarchy: ADMIN > DOCTOR > VIEWER
const ROLE_HIERARCHY: Record<UserRole, number> = {
  [UserRole.ADMIN]: 3,
  [UserRole.DOCTOR]: 2,
  [UserRole.VIEWER]: 1,
};

@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const requiredRoles = this.reflector.getAllAndOverride<UserRole[]>(
      ROLES_KEY,
      [context.getHandler(), context.getClass()],
    );

    if (!requiredRoles || requiredRoles.length === 0) {
      // No roles required, allow access
      return true;
    }

    const request = context.switchToHttp().getRequest();
    const user = request.user;

    if (!user || !user.role) {
      throw new ForbiddenException('User role not found');
    }

    const userRoleLevel = ROLE_HIERARCHY[user.role as UserRole];
    const hasRequiredRole = requiredRoles.some((requiredRole) => {
      const requiredRoleLevel = ROLE_HIERARCHY[requiredRole];
      return userRoleLevel >= requiredRoleLevel;
    });

    if (!hasRequiredRole) {
      throw new ForbiddenException(
        `Insufficient permissions. Required roles: ${requiredRoles.join(', ')}`,
      );
    }

    return true;
  }
}