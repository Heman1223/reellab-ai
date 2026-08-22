"""ReelLab AI service contracts — the Python mirror of `shared/schemas/`.

Import from here:

    from schemas import AudienceRequest, ContentDNA, SimulationResult

Keep this module in lockstep with `shared/schemas/*.ts`. See `shared/README.md`
for the contract rules.
"""

from .base import ReelLabModel
from .audience import AudienceGraph, AudienceRequest, AudienceSegment, SegmentAdjacency
from .persona import (
    AttentionProfile,
    ContentPreferences,
    DurationRange,
    EngagementProfile,
    Persona,
    PersonaGenerationRequest,
)
from .content import (
    AudioFeatures,
    CallToAction,
    ContentDNA,
    Hook,
    Scene,
    VideoAnalysisRequest,
    VisualFeatures,
)
from .simulation import (
    PersonaSimulationResult,
    PropagationWave,
    RunMetadata,
    SimulationRequest,
    SimulationStatus,
    ViewerAction,
)
from .result import AudienceSegmentResult, Bottleneck, SimulationResult, Warning
from .experiment import (
    CounterfactualExperiment,
    ExperimentRequest,
    ModificationType,
    Recommendation,
    Variant,
    VariantComparison,
)
from .evaluation import (
    ActualPerformance,
    EvaluationDataset,
    EvaluationItem,
    EvaluationMetrics,
    EvaluationRequest,
    Prediction,
)
from .envelope import Envelope, wrap

__all__ = [
    "ReelLabModel",
    "AudienceGraph",
    "AudienceRequest",
    "AudienceSegment",
    "SegmentAdjacency",
    "AttentionProfile",
    "ContentPreferences",
    "DurationRange",
    "EngagementProfile",
    "Persona",
    "PersonaGenerationRequest",
    "AudioFeatures",
    "CallToAction",
    "ContentDNA",
    "Hook",
    "Scene",
    "VideoAnalysisRequest",
    "VisualFeatures",
    "PersonaSimulationResult",
    "PropagationWave",
    "RunMetadata",
    "SimulationRequest",
    "SimulationStatus",
    "ViewerAction",
    "AudienceSegmentResult",
    "Bottleneck",
    "SimulationResult",
    "Warning",
    "CounterfactualExperiment",
    "ExperimentRequest",
    "ModificationType",
    "Recommendation",
    "Variant",
    "VariantComparison",
    "ActualPerformance",
    "EvaluationDataset",
    "EvaluationItem",
    "EvaluationMetrics",
    "EvaluationRequest",
    "Prediction",
    "Envelope",
    "wrap",
]
