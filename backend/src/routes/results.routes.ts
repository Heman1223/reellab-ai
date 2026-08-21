import { Router } from 'express';

import { getResultById } from '../controllers/resultsController';
import { asyncHandler } from '../utils/asyncHandler';

const router = Router();

router.get('/:id', asyncHandler(getResultById));

export default router;
