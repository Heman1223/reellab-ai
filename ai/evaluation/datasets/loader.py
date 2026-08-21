"""Evaluation datasets.

Ground truth lives in `data/evaluation/` — see that folder's README for what the
numbers mean and how to replace the placeholders with real creator analytics.

OWNER: Developer 1.
"""

from __future__ import annotations

from schemas import EvaluationDataset

import fixtures


def load_dataset(dataset_id: str | None = None) -> EvaluationDataset:
    """Load an evaluation dataset by id.

    Only one dataset exists for now, so `dataset_id` is accepted and ignored.
    The parameter is here so adding a second dataset does not change any call
    site.
    """
    dataset = fixtures.evaluation_dataset()
    _ = dataset_id
    return dataset


def actual_ranking(dataset: EvaluationDataset) -> list[str]:
    """Reel ids ordered by real-world performance, best first."""
    return [
        item.reel_id
        for item in sorted(dataset.items, key=lambda item: item.actual_rank)
    ]
