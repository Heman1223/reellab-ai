# `data/evaluation/`

Ground-truth data for the evaluation harness in [`ai/evaluation/`](../../ai/evaluation).

## The loop we are trying to close

```
historical reel → our simulation → predicted ranking
                                        ↕  compare
                          actual performance (this folder)
```

If ReelLab's predicted ranking of a creator's past reels does not correlate with
how those reels actually performed, the simulation is not measuring anything
real. That comparison is the honest test of the whole product.

## Files

| File | What it holds |
| --- | --- |
| `historical_reels.json` | Three reels with their real-world metrics and a ground-truth rank. |

## Adding real data

Replace the placeholder numbers with figures exported from a creator's
Instagram/TikTok analytics. Keep the shape identical:

- `actual.threeSecondRetention` — the metric our hook bottleneck predicts.
- `actual.shareRate` — the metric our propagation model predicts.
- `actualRank` — 1 is the best-performing reel in the set.

Do not commit anything that identifies a real creator without their permission.
