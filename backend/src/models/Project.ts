import { Schema, model } from 'mongoose';

/**
 * A creator's workspace: one audience brief plus everything derived from it.
 *
 * Schemas in this folder are deliberately thin. Persisting the AI payloads as
 * `Schema.Types.Mixed` means Developer 1 and Developer 2 can evolve the shape
 * of their output without a migration, and the authoritative definition stays
 * in `shared/schemas/`. Add real sub-schemas only where you need to query.
 */
const projectSchema = new Schema(
  {
    name: { type: String, required: true, trim: true },
    niche: { type: String, required: true },
    targetAudience: { type: String, required: true },
    secondaryAudience: { type: String },
    location: { type: String, required: true },
    language: { type: String, required: true },
    creatorGoal: { type: String, required: true },
    graphId: { type: String, index: true },
  },
  { timestamps: true },
);

export const Project = model('Project', projectSchema);
