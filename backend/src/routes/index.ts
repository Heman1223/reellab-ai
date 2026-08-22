import { Router } from 'express';

import audienceRoutes from './audience.routes';
import experimentsRoutes from './experiments.routes';
import healthRoutes from './health.routes';
import reelsRoutes from './reels.routes';
import resultsRoutes from './results.routes';
import simulationRoutes from './simulation.routes';

import configRoutes from './config.routes';

/**
 * `/api/v1` router.
 *
 * One `use` line per feature area. Each area lives in its own file so four
 * people adding routes at once touch four different files — this index is the
 * only shared line, and it changes about once per feature.
 */
const router = Router();

router.use('/health', healthRoutes);
router.use('/audience', audienceRoutes);
router.use('/reels', reelsRoutes);
router.use('/simulation', simulationRoutes);
router.use('/experiments', experimentsRoutes);
router.use('/results', resultsRoutes);
router.use('/config', configRoutes);

export default router;
