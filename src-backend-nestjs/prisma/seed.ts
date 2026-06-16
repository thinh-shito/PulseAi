import { PrismaClient, Role } from '@prisma/client';
import { PrismaPg } from '@prisma/adapter-pg';
import { Pool } from 'pg';
import * as bcrypt from 'bcrypt';
import * as dotenv from 'dotenv';
dotenv.config();

const connectionString = process.env.DATABASE_URL;
const pool = new Pool({ connectionString });
const adapter = new PrismaPg(pool);
const prisma = new PrismaClient({ adapter });

const SEED_USERS = [
  {
    email: 'admin@pulseai.hospital',
    password: 'AdminPass123!',
    fullName: 'System Administrator',
    role: Role.admin,
  },
  {
    email: 'doctor@pulseai.hospital',
    password: 'DoctorPass123!',
    fullName: 'Dr. Emily Chen',
    role: Role.doctor,
  },
  {
    email: 'viewer@pulseai.hospital',
    password: 'ViewerPass123!',
    fullName: 'Clinical Viewer',
    role: Role.viewer,
  },
];

async function main() {
  console.log('🌱 Starting database seeding...');
  
  for (const user of SEED_USERS) {
    const hashedPassword = await bcrypt.hash(user.password, 10);
    
    const upserted = await prisma.user.upsert({
      where: { email: user.email },
      update: {
        fullName: user.fullName,
        hashedPassword,
        role: user.role,
      },
      create: {
        email: user.email,
        fullName: user.fullName,
        hashedPassword,
        role: user.role,
        isActive: true,
      },
    });
    
    console.log(`  👤 Upserted user: ${upserted.email} [${upserted.role}]`);
  }
  
  console.log('🎉 Seeding completed successfully!');
}

main()
  .catch((e) => {
    console.error('❌ Error during seeding:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
