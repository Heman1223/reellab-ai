import { Schema, model } from 'mongoose';

/**
 * One node of a discovered audience graph.
 *
 * Stored flat with a `parentSegment` reference rather than nested, because the
 * frontend, the propagation engine and the results dashboard all want to look
 * segments up by id.
 */
const audienceSegmentSchema = new Schema(
  {
    segmentId: { type: String, required: true, index: true },
    graphId: { type: String, required: true, index: true },
    name: { type: String, required: true },
    description: { type: String, required: true },
    /** `null` for a root niche, otherwise a `segmentId`. */
    parentSegment: { type: String, default: null },
    characteristics: { type: [String], default: [] },
    relevanceScore: { type: Number, required: true, min: 0, max: 1 },
    estimatedShare: { type: Number, min: 0, max: 1 },
    rationale: { type: String },
  },
  { timestamps: true },
);

audienceSegmentSchema.index({ graphId: 1, segmentId: 1 }, { unique: true });

export const AudienceSegment = model('AudienceSegment', audienceSegmentSchema);
