import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
  ManyToOne,
  JoinColumn,
} from 'typeorm';
import { User } from './user.entity';

@Entity('audit_logs')
export class AuditLog {
  @PrimaryGeneratedColumn('uuid')
  log_id: string;

  @Column({ type: 'uuid', nullable: true })
  user_id: string;

  @ManyToOne(() => User)
  @JoinColumn({ name: 'user_id' })
  user: User;

  @Column({ length: 100 })
  action: string;

  @Column({ length: 100, nullable: true })
  resource_type: string;

  @Column({ type: 'uuid', nullable: true })
  resource_id: string;

  @Column({ type: 'jsonb', nullable: true })
  details: Record<string, any>;

  @Column({ length: 45, nullable: true })
  ip_address: string;

  @Column({ length: 255, nullable: true })
  user_agent: string;

  @CreateDateColumn()
  created_at: Date;

  // Note: No UpdateDateColumn - audit logs are append-only
}