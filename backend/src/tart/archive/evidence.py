"""Evidence level and how Attributions read (archive-records spec, Evidence level and
Attribution).

Both are computed from what the public can see, never stored or set: callers pass the
ids of the public records among those cited, so a withdrawn citation stops counting
and a Reinstatement brings it back without any change to the Claim.
"""

from collections.abc import Collection
from dataclasses import dataclass
from enum import StrEnum

from tart.archive.records import Artwork, Attribution, Certainty, RecordId, Ref


class EvidenceLevel(StrEnum):
    DOCUMENTED = "documented"
    """The Claim cites at least one public Source or Documentation item."""
    REPORTED = "reported"


def evidence_level(citations: Collection[Ref], public: Collection[RecordId]) -> EvidenceLevel:
    """The Evidence level of a Claim (an Attribution or a History event) with these citations.

    Record-level citations are not a Claim's: they never change an Evidence level.
    """
    if any(cited in public for cited in citations):
        return EvidenceLevel.DOCUMENTED
    return EvidenceLevel.REPORTED


@dataclass(frozen=True)
class ShownAttribution:
    """An Attribution as the public reads it."""

    attribution: Attribution
    certainty: Certainty
    """`confirmed` reads `probable` while the Attribution has no public citation."""
    evidence_level: EvidenceLevel


def shown_attribution(attribution: Attribution, public: Collection[RecordId]) -> ShownAttribution:
    level = evidence_level(attribution.citations, public)
    certainty = attribution.certainty
    if certainty is Certainty.CONFIRMED and level is EvidenceLevel.REPORTED:
        certainty = Certainty.PROBABLE
    return ShownAttribution(attribution, certainty, level)


@dataclass(frozen=True)
class AttributionReadout:
    """Who an Artwork is by, as the public reads it; the UI composes the words.

    With neither list it reads "Unknown artist"; several non-disputed Attributions are
    a collaboration, listed together; disputed ones are the competing alternatives,
    read "Disputed attribution: A or B".
    """

    attributed: tuple[ShownAttribution, ...]
    disputed: tuple[ShownAttribution, ...]

    @property
    def unknown(self) -> bool:
        return not self.attributed and not self.disputed


def attribution_readout(artwork: Artwork, public: Collection[RecordId]) -> AttributionReadout:
    """The readout of the Artwork's Attributions to public Artists, in their stored order.

    An Attribution to an Artist the public cannot see is left out, so an Artwork with
    only such Attributions reads like one without any.
    """
    shown = [
        shown_attribution(attribution, public)
        for attribution in artwork.attributions
        if attribution.artist in public
    ]
    return AttributionReadout(
        attributed=tuple(item for item in shown if item.certainty is not Certainty.DISPUTED),
        disputed=tuple(item for item in shown if item.certainty is Certainty.DISPUTED),
    )
