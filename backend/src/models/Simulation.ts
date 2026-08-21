import { Schema, model } from 'mongoose';

/** One simulation run and its full result. */
const simulationSchema = new Schema(
  {
    simulationId: { type: String, required: true, unique: true, index: true },
    projectId: { type: Schema.Types.ObjectId, ref: 'Project', index: true },
    reelId: { type: String, index: true },
    graphId: { type: String, index: true },
    /** Set when this run evaluates a counterfactual variant rather than the original. */
    variantId: { type: String, index: true },
    status: {
      type: String,
      enum: [
        'queued',
        'analyzing_content',
        'simulating_personas',
        'propagating',
        'reflecting',
        'completed',
        'failed',
        'partial',
      ],
      default: 'queued',
      index: true,
    },
    overallScore: { type: Number, min: 0, max: 1 },
    confidence: { type: Number, min: 0, max: 1 },
    /** Arrays from shared/schemas/result.ts. Owned by Developer 1. */
    audienceResults: { type: Schema.Types.Mixed, default: [] },
    propagationWaves: { type: Schema.Types.Mixed, default: [] },
    audienceSegmentResults: { type: Schema.Types.Mixed, default: [] },
    bottlenecks: { type: Schema.Types.Mixed, default: [] },
    warnings: { type: Schema.Types.Mixed, default: [] },
    /** `RunMetadata`: model, prompt version, latency, tokens, cost. */
    metadata: { type: Schema.Types.Mixed },
    completedAt: { type: Date },
  },
  { timestamps: true },
);

export const Simulation = model('Simulation', simulationSchema);
