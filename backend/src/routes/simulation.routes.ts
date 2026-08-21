import { Router } from 'express';

import { getSimulationById, postRunSimulation } from '../controllers/simulationController';
import { asyncHandler } from '../utils/asyncHandler';

const router = Router();

router.post('/run', asyncHandler(postRunSimulation));
router.get('/:id', asyncHandler(getSimulationById));

export default router;
