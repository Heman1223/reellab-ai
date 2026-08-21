import { Schema, model } from 'mongoose';

/** An uploaded video plus the Content DNA derived from it. */
const reelSchema = new Schema(
  {
    reelId: { type: String, required: true, unique: true, index: true },
    projectId: { type: Schema.Types.ObjectId, ref: 'Project', index: true },
    filename: { type: String, required: true },
    /** Server-side path. Never a browser blob URL. */
    storagePath: { type: String, required: true },
    sizeBytes: { type: Number, required: true },
    durationSeconds: { type: Number },
    status: {
      type: String,
      enum: ['uploaded', 'analyzing', 'analyzed', 'failed'],
      default: 'uploaded',
      index: true,
    },
    /** `ContentDNA` from shared/schemas/content.ts. Owned by Developer 2. */
    contentDna: { type: Schema.Types.Mixed },
    failureReason: { type: String },
  },
  { timestamps: true },
);

export const Reel = model('Reel', reelSchema);
