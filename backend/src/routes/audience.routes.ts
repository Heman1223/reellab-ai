import { Router } from 'express';

import { postDiscoverAudience } from '../controllers/audienceController';
import { asyncHandler } from '../utils/asyncHandler';

const router = Router();

router.post('/discover', asyncHandler(postDiscoverAudience));

export default router;
