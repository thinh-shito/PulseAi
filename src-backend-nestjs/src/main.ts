import { NestFactory } from '@nestjs/core';
import {
  FastifyAdapter,
  NestFastifyApplication,
} from '@nestjs/platform-fastify';
import { AppModule } from './app.module';
import { ValidationPipe } from '@nestjs/common';
import { HttpExceptionFilter } from './common/filters/http-exception.filter';
import contentParser from '@fastify/multipart';

async function bootstrap() {
  const app = await NestFactory.create<NestFastifyApplication>(
    AppModule,
    new FastifyAdapter(),
  );

  await app.register(contentParser);

  // Global prefixes and boundaries validation
  app.setGlobalPrefix('api/v1');
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
    }),
  );

  // Centralized HIPAA-compliant error filter
  app.useGlobalFilters(new HttpExceptionFilter());

  // Configure CORS
  app.enableCors({
    origin: (origin, callback) => {
      const allowed = process.env.ALLOWED_ORIGINS
        ? process.env.ALLOWED_ORIGINS.split(',')
        : ['http://localhost:3000'];

      if (
        !origin ||
        allowed.indexOf(origin) !== -1 ||
        origin.startsWith('http://localhost:')
      ) {
        callback(null, true);
      } else {
        callback(null, false);
      }
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  });

  const port = process.env.PORT ? parseInt(process.env.PORT, 10) : 8000;
  await app.listen(port, '0.0.0.0');
  console.log(
    `NestJS application successfully running on: http://localhost:${port}/api/v1`,
  );
}
void bootstrap();
