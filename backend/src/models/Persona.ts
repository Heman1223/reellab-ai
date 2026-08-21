import { Schema, model } from 'mongoose';

/**
 * A generated synthetic viewer.
 *
 * Personas are the expensive artefact in this system — generating them costs a
 * model call each. They are stored so a second simulation against the same
 * segment can reuse them instead of regenerating, which is the first cost
 * optimisation we will want (see docs/architecture.md#cost-aware-architecture).
 */
const personaSchema = new Schema(
  {
    personaId: { type: String, required: true, unique: true, index: true },
    segmentId: { type: String, required: true, index: true },
    graphId: { type: String, index: true },
    name: { type: String, required: true },
    demographicSummary: { type: String, required: true },
    interests: { type: [String], default: [] },
    behavioralTraits: { type: [String], default: [] },
    /** Profile objects from shared/schemas/persona.ts. Owned by Developer 1. */
    attentionProfile: { type: Schema.Types.Mixed, required: true },
    engagementProfile: { type: Schema.Types.Mixed, required: true },
    contentPreferences: { type: Schema.Types.Mixed, required: true },
    systemBrief: { type: String },
  },
  { timestamps: true },
);

export const Persona = model('Persona', personaSchema);
