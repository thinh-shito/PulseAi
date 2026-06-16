import { createParamDecorator, ExecutionContext } from '@nestjs/common';

/**
 * Custom decorator to retrieve the authenticated user from the request
 * Usage: @CurrentUser() user: any
 */
export const CurrentUser = createParamDecorator(
  (data: unknown, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    return request.user;
  },
);