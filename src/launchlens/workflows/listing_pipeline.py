from dataclasses import dataclass
from temporalio import workflow


@dataclass
class ListingPipelineInput:
    listing_id: str
    tenant_id: str


@workflow.defn
class ListingPipeline:
    """
    LaunchLens listing processing pipeline.

    ┌─────────────────────────────────────────────────────────────┐
    │  upload.created                                             │
    │       │                                                     │
    │       ▼                                                     │
    │  IngestPhotos ──► VisionTier1 ──► VisionTier2              │
    │                                       │                    │
    │                               CoverageAgent                │
    │                                       │                    │
    │                               PackagingAgent               │
    │                                       │                    │
    │                         [shadow_review signal?]            │
    │                                       │                    │
    │                         [human_review signal]              │
    │                                       │                    │
    │                              ContentAgent                  │
    │                                       │                    │
    │                              BrandAgent                    │
    │                                       │                    │
    │                           DistributionAgent                │
    └─────────────────────────────────────────────────────────────┘

    Note: LearningAgent is NOT part of this pipeline.
    It is a separate workflow triggered by human.* events during review.
    """

    def __init__(self) -> None:
        self._shadow_approved = False
        self._review_completed = False

    @workflow.run
    async def run(self, input: ListingPipelineInput) -> str:
        # Placeholder — agents implemented in Agent Pipeline plan
        # Each step will be: await workflow.execute_activity(AgentName.execute, ...)
        return f"pipeline_complete:{input.listing_id}"

    @workflow.signal
    async def shadow_review_approved(self) -> None:
        self._shadow_approved = True

    @workflow.signal
    async def human_review_completed(self) -> None:
        self._review_completed = True
