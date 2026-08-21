import mongoose from 'mongoose';
import { Reel } from '../src/models/Reel';

describe('Reel Mongoose Model', () => {
  it('validates a properly formed Reel document', () => {
    const validReel = new Reel({
      reelId: 'reel_12345',
      projectId: new mongoose.Types.ObjectId(),
      title: 'Fitness Hook Demo',
      filename: 'sample_video.mp4',
      originalFilename: 'my_workout_reel.mp4',
      storagePath: '/uploads/sample_video.mp4',
      mimeType: 'video/mp4',
      sizeBytes: 10485760,
      durationSeconds: 30,
      status: 'uploaded',
    });

    const error = validReel.validateSync();
    expect(error).toBeUndefined();
    expect(validReel.reelId).toBe('reel_12345');
    expect(validReel.status).toBe('uploaded');
    expect(validReel.sizeBytes).toBe(10485760);
  });

  it('defaults status to uploaded when not explicitly provided', () => {
    const reel = new Reel({
      reelId: 'reel_default_status',
      filename: 'video.mp4',
      storagePath: '/uploads/video.mp4',
      sizeBytes: 5000,
    });

    expect(reel.status).toBe('uploaded');
    const error = reel.validateSync();
    expect(error).toBeUndefined();
  });

  it('fails validation when required fields are missing', () => {
    const emptyReel = new Reel({});
    const error = emptyReel.validateSync();

    expect(error).toBeDefined();
    expect(error?.errors.reelId).toBeDefined();
    expect(error?.errors.filename).toBeDefined();
    expect(error?.errors.storagePath).toBeDefined();
    expect(error?.errors.sizeBytes).toBeDefined();
  });

  it('accepts all valid ReelStatus enum values', () => {
    const validStatuses = ['uploaded', 'processing', 'analyzing', 'analyzed', 'failed'] as const;

    for (const status of validStatuses) {
      const reel = new Reel({
        reelId: `reel_${status}`,
        filename: 'video.mp4',
        storagePath: '/uploads/video.mp4',
        sizeBytes: 1000,
        status,
      });

      const error = reel.validateSync();
      expect(error).toBeUndefined();
      expect(reel.status).toBe(status);
    }
  });

  it('rejects invalid status values', () => {
    const invalidReel = new Reel({
      reelId: 'reel_invalid',
      filename: 'video.mp4',
      storagePath: '/uploads/video.mp4',
      sizeBytes: 1000,
      status: 'unknown_status' as unknown as import('../src/models/Reel').ReelStatus,
    });

    const error = invalidReel.validateSync();
    expect(error).toBeDefined();
    expect(error?.errors.status).toBeDefined();
  });

  it('rejects negative sizeBytes or durationSeconds', () => {
    const negativeReel = new Reel({
      reelId: 'reel_negative',
      filename: 'video.mp4',
      storagePath: '/uploads/video.mp4',
      sizeBytes: -100,
      durationSeconds: -5,
    });

    const error = negativeReel.validateSync();
    expect(error).toBeDefined();
    expect(error?.errors.sizeBytes).toBeDefined();
    expect(error?.errors.durationSeconds).toBeDefined();
  });
});
