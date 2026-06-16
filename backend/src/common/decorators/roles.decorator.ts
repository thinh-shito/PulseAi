import { SetMetadata } from '@nestjs/common';
import { UserRole } from '../../core/security/roles.guard';

export const ROLES_KEY = 'roles';

/**
 * Decorator to specify required roles for a route handler
 * Usage: @Roles(UserRole.ADMIN, UserRole.DOCTOR)
 */
export const Roles = (...roles: UserRole[]) => SetMetadata(ROLES_KEY, roles);