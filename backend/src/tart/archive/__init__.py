"""The archive domain: record values and rules, with no framework or persistence imports.

The write operation (`apply_changeset`) is the only way records change; it reaches
persistence through the `ArchiveStore` port.
"""

from tart.archive.changeset import (
    AddItem,
    ChangeItem,
    Changeset,
    Create,
    Operation,
    RemoveItem,
    SetField,
)
from tart.archive.errors import ArchiveRuleViolation
from tart.archive.geometry import Boundary, Geometry, GeometryKind
from tart.archive.ports import ArchiveStore
from tart.archive.records import (
    Area,
    Artist,
    ArtistKind,
    Artwork,
    Attribution,
    Certainty,
    CrewMembership,
    DocumentationItem,
    Kind,
    Location,
    LocationTitle,
    Medium,
    New,
    Record,
    RecordId,
    Ref,
    RightsBasis,
    Series,
    Site,
    Source,
    location_title,
)
from tart.archive.revisions import Provenance, Revision
from tart.archive.rules import InstanceRules
from tart.archive.slug import record_path_segment, slugify
from tart.archive.uncertain_date import DateRange, Period, Precision, Qualifier, UncertainDate
from tart.archive.write import apply_changeset

__all__ = [
    "AddItem",
    "ArchiveRuleViolation",
    "ArchiveStore",
    "Area",
    "Artist",
    "ArtistKind",
    "Artwork",
    "Attribution",
    "Boundary",
    "Certainty",
    "ChangeItem",
    "Changeset",
    "Create",
    "CrewMembership",
    "DateRange",
    "DocumentationItem",
    "Geometry",
    "GeometryKind",
    "InstanceRules",
    "Kind",
    "Location",
    "LocationTitle",
    "Medium",
    "New",
    "Operation",
    "Period",
    "Precision",
    "Provenance",
    "Qualifier",
    "Record",
    "RecordId",
    "Ref",
    "RemoveItem",
    "Revision",
    "RightsBasis",
    "Series",
    "SetField",
    "Site",
    "Source",
    "UncertainDate",
    "apply_changeset",
    "location_title",
    "record_path_segment",
    "slugify",
]
