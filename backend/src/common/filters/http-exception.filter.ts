import {
  ExceptionFilter,
  Catch,
  ArgumentsHost,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { Request, Response } from 'express';

@Catch()
export class HttpExceptionFilter implements ExceptionFilter {
  private readonly logger = new Logger(HttpExceptionFilter.name);

  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();

    const status =
      exception instanceof HttpException
        ? exception.getStatus()
        : HttpStatus.INTERNAL_SERVER_ERROR;

    const exceptionResponse =
      exception instanceof HttpException
        ? exception.getResponse()
        : null;

    let message = 'Internal server error';
    let errors: any = null;

    if (exception instanceof HttpException) {
      if (typeof exceptionResponse === 'string') {
        message = exceptionResponse;
      } else if (exceptionResponse && typeof exceptionResponse === 'object') {
        const resObj = exceptionResponse as any;
        message = resObj.message || exception.message;
        errors = resObj.errors || null;
      } else {
        message = exception.message;
      }
    } else if (exception instanceof Error) {
      message = exception.message;
    }

    // Log the error (without logging any PHI that might be in the request body/params)
    this.logger.error(
      `${request.method} ${request.url} - Status: ${status} - Error: ${message}`,
      exception instanceof Error ? exception.stack : undefined,
    );

    // HIPAA Compliance: Do not expose stack traces or raw database messages to clients
    const isProduction = process.env.NODE_ENV === 'production';
    const cleanMessage = status === HttpStatus.INTERNAL_SERVER_ERROR && isProduction
      ? 'An unexpected error occurred. Please contact support.'
      : message;

    response.status(status).json({
      statusCode: status,
      timestamp: new Date().toISOString(),
      path: request.url,
      message: cleanMessage,
      ...(errors ? { errors } : {}),
      ...(!isProduction && exception instanceof Error ? { stack: exception.stack } : {}),
    });
  }
}