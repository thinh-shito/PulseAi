import 'reflect-metadata';
import { DataSource } from 'typeorm';
import * as bcrypt from 'bcryptjs';
import { User, UserRole } from './common/entities/user.entity';
import { Workflow } from './common/entities/workflow.entity';
import { AuditLog } from './common/entities/audit-log.entity';
import { PATemplate } from './common/entities/pa-template.entity';

const SEED_USERS = [
    {
        email: 'admin@pulseai.hospital',
        password: 'AdminPass123!',
        full_name: 'System Administrator',
        role: UserRole.ADMIN,
    },
    {
        email: 'doctor@pulseai.hospital',
        password: 'DoctorPass123!',
        full_name: 'Dr. Emily Chen',
        role: UserRole.DOCTOR,
    },
    {
        email: 'viewer@pulseai.hospital',
        password: 'ViewerPass123!',
        full_name: 'Clinical Viewer',
        role: UserRole.VIEWER,
    },
];

async function seed() {
    const databaseUrl = process.env.DATABASE_URL
        || 'postgresql://pulseai:pulseai_secret@postgres:5432/pulseai_db';

    const dataSource = new DataSource({
        type: 'postgres',
        url: databaseUrl,
        entities: [User, Workflow, AuditLog, PATemplate],
        synchronize: true,
        logging: true,
    });

    await dataSource.initialize();
    console.log('🔌 Database connected');

    const userRepo = dataSource.getRepository(User);

    for (const userData of SEED_USERS) {
        const existing = await userRepo.findOne({ where: { email: userData.email } });

        const hashedPassword = bcrypt.hashSync(userData.password, 10);

        if (existing) {
            existing.hashed_password = hashedPassword;
            existing.full_name = userData.full_name;
            existing.role = userData.role;
            existing.is_active = true;
            await userRepo.save(existing);
            console.log(`  🔄 Updated: ${userData.email} [${userData.role}]`);
        } else {
            const user = userRepo.create({
                email: userData.email,
                hashed_password: hashedPassword,
                full_name: userData.full_name,
                role: userData.role,
                is_active: true,
            });
            await userRepo.save(user);
            console.log(`  ✅ Created: ${userData.email} [${userData.role}]`);
        }
    }

    await dataSource.destroy();
    console.log('\n🎉 Seed complete!');
}

seed().catch((err) => {
    console.error('❌ Seed failed:', err);
    process.exit(1);
});