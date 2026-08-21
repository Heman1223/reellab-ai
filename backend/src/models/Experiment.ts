import { Schema, model } from 'mongoose';

/** A counterfactual experiment: one hypothesis, N variants, one comparison. */
const experimentSchema = new Schema(
  {
    experimentId: { type: String, required: true, unique: true, index: true },
    originalSimulationId: { type: String, required: true, index: true },
    hypothesis: { type: String },
    modificationType: {
      type: String,
      enum: ['hook', 'duration', 'cta', 'tone', 'pacing', 'audience'],
      required: true,
    },
    status: {
      type: String,
      enum: ['queued', 'generating', 'simulating', 'completed', 'failed'],
      default: 'queued',
      index: true,
    },
    /** Shapes from shared/schemas/experiment.ts. Dev 2 generates, Dev 1 simulates. */
    variants: { type: Schema.Types.Mixed, default: [] },
    comparison: { type: Schema.Types.Mixed, default: [] },
    recommendation: { type: Schema.Types.Mixed },
    metadata: { type: Schema.Types.Mixed },
    completedAt: { type: Date },
  },
  { timestamps: true },
);

export const Experiment = model('Experiment', experimentSchema);
