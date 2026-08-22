import { Router } from 'express';
import { config } from '../config/env';

const router = Router();

router.get('/', (_req, res) => {
  res.json({
    data: {
      maxUploadMb: Math.floor(config.maxUploadBytes / (1024 * 1024)),
    },
    mock: false
  });
});

export default router;
