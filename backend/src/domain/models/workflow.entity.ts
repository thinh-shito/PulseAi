import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
  UpdateDateColumn,
  ManyToOne,
  JoinColumn,
} from 'typeorm';
import { User } from './user.entity';

export enum WorkflowStatus {
  DRAFT = 'DRAFT',
  IN_REVIEW = 'IN_REVIEW',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED',
}

@Entity('workflows')
export class Workflow {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ length: 100 })
  patient_id: string;

  @Column({ length: 200 })
  patient_name: string;

  @Column({ length: 200 })
  insurance_provider: string;

  @Column({ length: 50 })
  procedure_code: string;

  @Column({ length: 50 })
  diagnosis_code: string;

  @Column({ type: 'text' })
  clinical_notes: string;

  @Column({
    type: 'enum',
    enum: WorkflowStatus,
    default: WorkflowStatus.DRAFT,
  })
  status: WorkflowStatus;

  @Column({ type: 'uuid', nullable: true })
  template_id: string;

  @Column({ type: 'uuid' })
  created_by: string;

  @ManyToOne(() => User)
  @JoinColumn({ name: 'created_by' })
  user: User;

  @Column({ type: 'text', nullable: true })
  generated_document_path: string;

  @CreateDateColumn()
  created_at: Date;

  @UpdateDateColumn()
  updated_at: Date;
}
