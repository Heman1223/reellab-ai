import { Schema, model, type Document, type Types } from 'mongoose';
import type { ContentDNA } from '@shared/schemas/content';

export type ReelStatus = 'uploaded' | 'processing' | 'analyzing' | 'analyzed' | 'failed';

export interface IReel {
  reelId: string;
  projectId?: Types.ObjectId;
  title?: string;
  filename: string;
  originalFilename?: string;
  storagePath: string;
  mimeType?: string;
  sizeBytes: number;
  durationSeconds?: number;
  status: ReelStatus;
  contentDna?: ContentDNA | Record<string, unknown>;
  failureReason?: string;
  createdAt?: Date;
  updatedAt?: Date;
}

export type ReelDocument = IReel & Document;

/** An uploaded video plus the Content DNA derived from it. */
export const reelSchema = new Schema<IReel>(
  {
    reelId: { type: String, required: true, unique: true, index: true, trim: true },
    projectId: { type: Schema.Types.ObjectId, ref: 'Project', index: true },
    title: { type: String, trim: true },
    filename: { type: String, required: true, trim: true },
    originalFilename: { type: String, trim: true },
    /** Server-side path. Never a browser blob URL. */
    storagePath: { type: String, required: true, trim: true },
    mimeType: { type: String, trim: true },
    sizeBytes: { type: Number, required: true, min: 0 },
    durationSeconds: { type: Number, min: 0 },
    status: {
      type: String,
      enum: ['uploaded', 'processing', 'analyzing', 'analyzed', 'failed'],
      default: 'uploaded',
      index: true,
    },
    /** `ContentDNA` from shared/schemas/content.ts. Owned by Developer 2. */
    contentDna: { type: Schema.Types.Mixed },
    failureReason: { type: String },
  },
  { timestamps: true },
);

export const Reel = model<IReel>('Reel', reelSchema);
