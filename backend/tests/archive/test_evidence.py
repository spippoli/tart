"""Evidence level and how Attributions read (archive-records spec, Evidence level and
Attribution). Every record here is fictional.

Withdrawal belongs to Rights and legal actions; here a withdrawn record is simply one
missing from the set of public ids.
"""

from dataclasses import fields

from archive_fixtures import artwork

from tart.archive import (
    Attribution,
    Certainty,
    EvidenceLevel,
    HistoryEvent,
    attribution_readout,
    evidence_level,
    shown_attribution,
)

ARTIST_A, ARTIST_B, ARTIST_C = 10, 11, 12
SOURCE, PHOTO, RECORD_SOURCE = 20, 21, 22
PUBLIC = frozenset({ARTIST_A, ARTIST_B, ARTIST_C, SOURCE, PHOTO, RECORD_SOURCE})


# Criterion 5.


def test_criterion_5_a_claim_citing_a_public_record_reads_documented() -> None:
    assert evidence_level((SOURCE,), PUBLIC) is EvidenceLevel.DOCUMENTED
    assert evidence_level((PHOTO,), PUBLIC) is EvidenceLevel.DOCUMENTED


def test_criterion_5_a_claim_citing_nothing_reads_reported() -> None:
    assert evidence_level((), PUBLIC) is EvidenceLevel.REPORTED


def test_criterion_5_no_claim_has_a_field_that_sets_its_evidence_level() -> None:
    for claim in (Attribution, HistoryEvent):
        names = {field.name for field in fields(claim)}
        assert not names & {"evidence_level", "evidence", "documented", "verified"}


# Criterion 6.


def test_criterion_6_a_record_level_source_does_not_document_a_claim() -> None:
    record = artwork(
        1,
        sources=(RECORD_SOURCE,),
        attributions=(Attribution(ARTIST_A, Certainty.PROBABLE),),
    )

    shown = attribution_readout(record, PUBLIC).attributed

    assert [item.evidence_level for item in shown] == [EvidenceLevel.REPORTED]
    assert all(
        evidence_level(event.citations, PUBLIC) is EvidenceLevel.REPORTED
        for event in record.history_events
    )


# Criterion 8.


def test_criterion_8_an_artwork_without_attributions_reads_unknown_artist() -> None:
    readout = attribution_readout(artwork(1), PUBLIC)

    assert readout.unknown
    assert (readout.attributed, readout.disputed) == ((), ())


def test_criterion_8_several_non_disputed_attributions_are_all_listed() -> None:
    record = artwork(
        1,
        attributions=(
            Attribution(ARTIST_A, Certainty.CONFIRMED, citations=(SOURCE,)),
            Attribution(ARTIST_B, Certainty.PROBABLE),
        ),
    )

    readout = attribution_readout(record, PUBLIC)

    assert not readout.unknown
    assert [(item.attribution.artist, item.certainty) for item in readout.attributed] == [
        (ARTIST_A, Certainty.CONFIRMED),
        (ARTIST_B, Certainty.PROBABLE),
    ]
    assert readout.disputed == ()


def test_criterion_8_disputed_attributions_are_the_alternatives() -> None:
    record = artwork(
        1,
        attributions=(
            Attribution(ARTIST_A, Certainty.DISPUTED, note="Fictional: style matches."),
            Attribution(ARTIST_B, Certainty.DISPUTED, citations=(SOURCE,)),
        ),
    )

    readout = attribution_readout(record, PUBLIC)

    assert readout.attributed == ()
    assert [item.attribution.artist for item in readout.disputed] == [ARTIST_A, ARTIST_B]
    assert [item.evidence_level for item in readout.disputed] == [
        EvidenceLevel.REPORTED,
        EvidenceLevel.DOCUMENTED,
    ]


def test_an_attribution_to_an_artist_the_public_cannot_see_is_left_out() -> None:
    record = artwork(1, attributions=(Attribution(ARTIST_C, Certainty.PROBABLE),))

    assert attribution_readout(record, PUBLIC - {ARTIST_C}).unknown


# Criterion 53, the reading side.


def test_criterion_53_a_claim_whose_only_citations_are_withdrawn_reads_reported() -> None:
    withdrawn = PUBLIC - {SOURCE, PHOTO}

    assert evidence_level((SOURCE, PHOTO), withdrawn) is EvidenceLevel.REPORTED
    assert evidence_level((SOURCE, PHOTO), PUBLIC - {SOURCE}) is EvidenceLevel.DOCUMENTED


def test_criterion_53_confirmed_without_a_public_citation_reads_probable_until_reinstated() -> None:
    confirmed = Attribution(ARTIST_A, Certainty.CONFIRMED, citations=(SOURCE,))

    hidden = shown_attribution(confirmed, PUBLIC - {SOURCE})
    reinstated = shown_attribution(confirmed, PUBLIC)

    assert (hidden.certainty, hidden.evidence_level) == (
        Certainty.PROBABLE,
        EvidenceLevel.REPORTED,
    )
    assert hidden.attribution.certainty is Certainty.CONFIRMED  # stored unchanged
    assert (reinstated.certainty, reinstated.evidence_level) == (
        Certainty.CONFIRMED,
        EvidenceLevel.DOCUMENTED,
    )


def test_criterion_53_a_shown_probable_attribution_is_listed_not_disputed() -> None:
    record = artwork(
        1,
        attributions=(
            Attribution(ARTIST_A, Certainty.CONFIRMED, citations=(SOURCE,)),
            Attribution(ARTIST_B, Certainty.PROBABLE),
        ),
    )

    readout = attribution_readout(record, PUBLIC - {SOURCE})

    assert [item.certainty for item in readout.attributed] == [
        Certainty.PROBABLE,
        Certainty.PROBABLE,
    ]
