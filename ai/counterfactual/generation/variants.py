"""Variant generation — the "what if" step.

    generate_variants(content, simulation, modification_type, count) -> list[Variant]

The model is given the reel *and* the diagnosis of why it underperformed, then
asked to propose specific changes that would address that diagnosis. Not generic
best practice — a fix aimed at the bottleneck this particular reel actually hit.

Each variant carries a `predicted_content_dna`: the Content DNA the reel would
have if the change were made. That is what makes the counterfactual cheap. The
creator never re-edits the video to find out whether the change was worth making.

Developer 2 owns this file. Developer 1 owns the simulation that judges its
output — which is the right split, because the generator should not also be the
judge.

OWNER: Developer 2.
"""

from __future__ import annotations

import uuid

from llm import llm, with_fixture_fallback
from logging_utils import get_logger, log_event
from schemas import ContentDNA, ModificationType, SimulationResult, Variant

import fixtures

logger = get_logger("counterfactual.generation")

PROMPT_VERSION = "variant-generation-v0"

#: What each lever is allowed to change. Keeps a "change the hook" experiment
#: from quietly rewriting the whole reel, which would make the comparison
#: meaningless.
MODIFICATION_BRIEFS: dict[str, str] = {
    "hook": "Rewrite only the opening seconds. Everything after the hook stays as it is.",
    "duration": "Propose a shorter cut. Say which scenes are dropped or compressed.",
    "cta": "Change only the call to action — what it asks for, how it is phrased, and when it lands.",
    "tone": "Keep the same information and delivery structure, but shift the tone.",
    "pacing": "Change cut rhythm and speaking pace. The content itself stays the same.",
    "audience": "Keep the reel unchanged and re-aim it at a different audience segment.",
}


def _build_prompt(
    content: ContentDNA,
    simulation: SimulationResult,
    modification_type: ModificationType,
    count: int,
    instruction: str | None,
) -> str:
    bottlenecks = "\n".join(
        f"- [{bottleneck.stage}] {bottleneck.description}\n"
        f"  Likely cause: {bottleneck.likely_cause} "
        f"(severity {bottleneck.severity:.2f}, confidence {bottleneck.confidence:.2f})"
        for bottleneck in simulation.bottlenecks
    ) or "- (no bottlenecks identified)"

    weakest = sorted(simulation.audience_segment_results, key=lambda r: r.score)[:2]
    weak_text = "\n".join(
        f"- {result.segment_name}: {result.score:.2f} ({result.verdict})" for result in weakest
    ) or "- (no segment breakdown)"

    return f"""A reel underperformed. Propose {count} specific alternatives.

Current opening ({content.hook.duration_seconds:.1f}s): "{content.hook.text}"
Duration: {content.duration_seconds:.0f}s. Tone: {content.tone}. Topic: {content.topic}.
Current CTA: {content.cta.text or "none"}
Overall score: {simulation.overall_score:.2f}

Where it broke:
{bottlenecks}

Weakest segments:
{weak_text}

Lever for this experiment: {modification_type}
{MODIFICATION_BRIEFS.get(modification_type, "")}
{f"Creator's steer: {instruction}" if instruction else ""}

CRITICAL RULES:
1. Change *only* what this lever allows. If modifying the CTA, do not redesign the whole reel. If modifying the hook, do not arbitrarily alter unrelated properties. If modifying pacing, focus strictly on pacing/cuts/timing.
2. A variant that changes several unrelated things at once cannot be attributed to any one of them, rendering the comparison worthless.
3. For each variant give: a short label, what changed and why it addresses the bottleneck above, the concrete new asset (the actual rewritten line, not a description of one), and the predicted Content DNA the reel would have after the change.
4. Make the variants genuinely different from each other. Two rephrasings of the same idea waste a simulation run.

Return JSON matching a list of the Variant schema."""


async def _generate_with_model(
    content: ContentDNA,
    simulation: SimulationResult,
    modification_type: ModificationType,
    count: int,
    instruction: str | None,
) -> list[Variant]:
    result = await llm.complete_json(
        prompt=_build_prompt(content, simulation, modification_type, count, instruction),
        prompt_version=PROMPT_VERSION,
        tier="reasoning",
    )
    raw = result.data if isinstance(result.data, list) else [result.data]
    
    try:
        variants = []
        for item in raw:
            # Handle case where LLM returns {"variants": [...]} instead of [...]
            if isinstance(item, dict) and "variants" in item and isinstance(item["variants"], list):
                for subitem in item["variants"]:
                    v = Variant.model_validate(subitem).model_copy(
                        update={"id": subitem.get("id") or f"var_{uuid.uuid4().hex[:6]}"}
                    )
                    variants.append(v)
            else:
                v = Variant.model_validate(item).model_copy(
                    update={"id": item.get("id") or f"var_{uuid.uuid4().hex[:6]}"}
                )
                variants.append(v)
        return variants[:count]
    except Exception as e:
        raise MalformedModelOutputError(f"Validation failed for Variant: {str(e)}") from e


def _fixture_variants(count: int) -> list[Variant]:
    return fixtures.counterfactual_experiment().variants[:count]


async def generate_variants(
    content: ContentDNA,
    simulation: SimulationResult,
    modification_type: ModificationType = "hook",
    count: int = 2,
    instruction: str | None = None,
) -> tuple[list[Variant], bool]:
    \"\"\"Generate counterfactual variants. Returns `(variants, mock)`.\"\"\"
    if count <= 0:
        return [], False

    variants, mock = await with_fixture_fallback(
        "counterfactual.generate",
        lambda: _generate_with_model(content, simulation, modification_type, count, instruction),
        lambda: _fixture_variants(count),
    )

    log_event(
        logger,
        "variants_generated",
        modification_type=modification_type,
        count=len(variants),
        mock=mock,
    )
    return variants, mock
