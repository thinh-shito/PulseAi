import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
} from 'typeorm';

@Entity('audit_logs')
export class AuditLog {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'uuid' })
  user_id: string;

  @Column()
  action: string;

  @Column({ nullable: true })
  patient_id: string;

  @Column({ type: 'uuid', nullable: true })
  workflow_id: string;

  @Column({ nullable: true })
  resource_type: string;

  @Column({ nullable: true })
  resource_id: string;

  @Column({ nullable: true })
  ip_address: string;

  @CreateDateColumn()
  created_at: Date;
}