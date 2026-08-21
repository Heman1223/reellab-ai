import { Router } from 'express';

import { getExperimentById, postCreateExperiment } from '../controllers/experimentsController';
import { asyncHandler } from '../utils/asyncHandler';

const router = Router();

router.post('/', asyncHandler(postCreateExperiment));
router.get('/:id', asyncHandler(getExperimentById));

export default router;
