from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DraftDocumentSpec:
    document_type: str
    title: str
    activity_title: str
    instruction: str


@dataclass(frozen=True)
class DraftingPacket:
    subcategory: str
    pleading_type: str
    documents: tuple[DraftDocumentSpec, ...]


NOTICE_OF_MOTION_AND_AFFIDAVIT = "Notice of Motion + Supporting Affidavit"
ORIGINATING_SUMMONS_AND_AFFIDAVIT = "Originating Summons + Supporting Affidavit"
PLAINT_AND_VERIFYING_AFFIDAVIT = "Plaint + Verifying Affidavit"


INJUNCTION_PACKET = DraftingPacket(
    subcategory="Temporary Injunction",
    pleading_type=NOTICE_OF_MOTION_AND_AFFIDAVIT,
    documents=(
        DraftDocumentSpec(
            document_type="injunction_motion",
            title="Notice of Motion for Temporary Injunction",
            activity_title="Drafting Notice of Motion",
            instruction=(
                "Draft a Notice of Motion for temporary injunction in an Environment and "
                "Land Court matter. Include the court heading, certificate-style urgency "
                "context only if the facts justify it, prayers, grounds, and a concise "
                "legal basis tied to the supplied facts and retrieved Kenyan authorities."
            ),
        ),
        DraftDocumentSpec(
            document_type="supporting_affidavit",
            title="Supporting Affidavit",
            activity_title="Drafting Supporting Affidavit",
            instruction=(
                "Draft a Supporting Affidavit for the temporary injunction application. "
                "Use numbered deposition paragraphs, preserve a clear fact chronology, "
                "identify anonymized parties and land references, refer to exhibits only "
                "when supported by the facts, and avoid legal argument that belongs in "
                "submissions or grounds."
            ),
        ),
    ),
)


ADVERSE_POSSESSION_PACKET = DraftingPacket(
    subcategory="Adverse Possession",
    pleading_type=ORIGINATING_SUMMONS_AND_AFFIDAVIT,
    documents=(
        DraftDocumentSpec(
            document_type="adverse_possession_originating_summons",
            title="Originating Summons for Adverse Possession",
            activity_title="Drafting Originating Summons",
            instruction=(
                "Draft an Originating Summons for adverse possession in the Environment "
                "and Land Court. Include the court heading, parties, questions for "
                "determination, orders sought, a concise legal basis, and relief tied "
                "strictly to the masked possession facts and retrieved Kenyan authorities."
            ),
        ),
        DraftDocumentSpec(
            document_type="adverse_possession_supporting_affidavit",
            title="Supporting Affidavit for Adverse Possession",
            activity_title="Drafting Supporting Affidavit",
            instruction=(
                "Draft a Supporting Affidavit for the adverse possession summons. Use "
                "numbered factual depositions covering entry, possession, continuity, "
                "openness, exclusivity, interruption if any, and land reference details "
                "only as supplied by the masked facts."
            ),
        ),
    ),
)


TRESPASS_PLAINT_PACKET = DraftingPacket(
    subcategory="Trespass/Eviction",
    pleading_type=PLAINT_AND_VERIFYING_AFFIDAVIT,
    documents=(
        DraftDocumentSpec(
            document_type="trespass_plaint",
            title="Plaint for Trespass and Eviction Relief",
            activity_title="Drafting Plaint",
            instruction=(
                "Draft a Plaint for an Environment and Land Court trespass or eviction "
                "claim. Include court heading, parties, jurisdiction, material facts, "
                "particulars of trespass or interference, prayers, and a legal basis "
                "grounded only in supplied facts and retrieved Kenyan authorities."
            ),
        ),
        DraftDocumentSpec(
            document_type="verifying_affidavit",
            title="Verifying Affidavit",
            activity_title="Drafting Verifying Affidavit",
            instruction=(
                "Draft a concise Verifying Affidavit confirming the truth of the plaint. "
                "Use numbered paragraphs, preserve anonymized placeholders, and avoid "
                "adding facts, dates, exhibits, or valuation details not supplied."
            ),
        ),
    ),
)


BOUNDARY_TITLE_PLAINT_PACKET = DraftingPacket(
    subcategory="Boundary/Title Dispute",
    pleading_type=PLAINT_AND_VERIFYING_AFFIDAVIT,
    documents=(
        DraftDocumentSpec(
            document_type="boundary_title_plaint",
            title="Plaint for Boundary or Title Dispute",
            activity_title="Drafting Plaint",
            instruction=(
                "Draft a Plaint for an Environment and Land Court boundary or title "
                "dispute. Include court heading, parties, jurisdiction, material facts, "
                "title or boundary issue, relief sought, and legal basis tied to the "
                "retrieved Kenyan authorities without resolving disputed ownership."
            ),
        ),
        DraftDocumentSpec(
            document_type="verifying_affidavit",
            title="Verifying Affidavit",
            activity_title="Drafting Verifying Affidavit",
            instruction=(
                "Draft a Verifying Affidavit for the plaint. Keep it factual, numbered, "
                "and limited to confirming the pleadings and the supplied masked facts."
            ),
        ),
    ),
)


PROCEDURAL_APPLICATION_PACKET = DraftingPacket(
    subcategory="Procedural Application",
    pleading_type=NOTICE_OF_MOTION_AND_AFFIDAVIT,
    documents=(
        DraftDocumentSpec(
            document_type="procedural_notice_of_motion",
            title="Notice of Motion for Procedural Relief",
            activity_title="Drafting Notice of Motion",
            instruction=(
                "Draft a Notice of Motion for procedural relief in the Environment and "
                "Land Court. Include the court heading, prayers, grounds, procedural "
                "basis, and a concise legal basis tied to the masked facts and retrieved "
                "Kenyan authorities."
            ),
        ),
        DraftDocumentSpec(
            document_type="procedural_supporting_affidavit",
            title="Supporting Affidavit for Procedural Application",
            activity_title="Drafting Supporting Affidavit",
            instruction=(
                "Draft a Supporting Affidavit for the procedural application. Use "
                "numbered factual depositions, explain the procedural history from the "
                "masked facts, and avoid unsupported merits arguments or invented dates."
            ),
        ),
    ),
)


APPLICATION_PACKETS = {
    ("Trespass/Eviction", NOTICE_OF_MOTION_AND_AFFIDAVIT): DraftingPacket(
        subcategory="Trespass/Eviction",
        pleading_type=NOTICE_OF_MOTION_AND_AFFIDAVIT,
        documents=(
            DraftDocumentSpec(
                document_type="trespass_notice_of_motion",
                title="Notice of Motion for Trespass or Eviction Relief",
                activity_title="Drafting Notice of Motion",
                instruction=(
                    "Draft a Notice of Motion for interim relief in a trespass or "
                    "eviction dispute. Include court heading, prayers preserving the "
                    "property or occupation, grounds tied to the masked facts, and a "
                    "legal basis from retrieved Kenyan authorities."
                ),
            ),
            DraftDocumentSpec(
                document_type="trespass_supporting_affidavit",
                title="Supporting Affidavit for Trespass or Eviction Application",
                activity_title="Drafting Supporting Affidavit",
                instruction=(
                    "Draft a Supporting Affidavit for the trespass or eviction "
                    "application. Use numbered factual depositions, preserve the "
                    "chronology, and avoid unsupported ownership conclusions, exhibits, "
                    "valuation figures, or dates."
                ),
            ),
        ),
    ),
    ("Boundary/Title Dispute", NOTICE_OF_MOTION_AND_AFFIDAVIT): DraftingPacket(
        subcategory="Boundary/Title Dispute",
        pleading_type=NOTICE_OF_MOTION_AND_AFFIDAVIT,
        documents=(
            DraftDocumentSpec(
                document_type="boundary_title_notice_of_motion",
                title="Notice of Motion for Boundary or Title Preservation",
                activity_title="Drafting Notice of Motion",
                instruction=(
                    "Draft a Notice of Motion for interim preservation in a boundary "
                    "or title dispute. Include court heading, prayers preserving the "
                    "register, occupation, boundaries, or status quo as justified by "
                    "the facts, grounds, and retrieved Kenyan authority support."
                ),
            ),
            DraftDocumentSpec(
                document_type="boundary_title_supporting_affidavit",
                title="Supporting Affidavit for Boundary or Title Application",
                activity_title="Drafting Supporting Affidavit",
                instruction=(
                    "Draft a Supporting Affidavit for the boundary or title application. "
                    "Use numbered factual depositions, keep the title or boundary issue "
                    "neutral, and do not invent survey reports, registry entries, or "
                    "fraud allegations not supplied in the masked facts."
                ),
            ),
        ),
    ),
}

_PACKETS_BY_KEY = {
    (INJUNCTION_PACKET.subcategory, INJUNCTION_PACKET.pleading_type): INJUNCTION_PACKET,
    (
        ADVERSE_POSSESSION_PACKET.subcategory,
        ADVERSE_POSSESSION_PACKET.pleading_type,
    ): ADVERSE_POSSESSION_PACKET,
    (
        TRESPASS_PLAINT_PACKET.subcategory,
        TRESPASS_PLAINT_PACKET.pleading_type,
    ): TRESPASS_PLAINT_PACKET,
    (
        BOUNDARY_TITLE_PLAINT_PACKET.subcategory,
        BOUNDARY_TITLE_PLAINT_PACKET.pleading_type,
    ): BOUNDARY_TITLE_PLAINT_PACKET,
    (
        PROCEDURAL_APPLICATION_PACKET.subcategory,
        PROCEDURAL_APPLICATION_PACKET.pleading_type,
    ): PROCEDURAL_APPLICATION_PACKET,
    **APPLICATION_PACKETS,
}

DEFAULT_PLEADING_TYPE_BY_SUBCATEGORY = {
    "Temporary Injunction": NOTICE_OF_MOTION_AND_AFFIDAVIT,
    "Adverse Possession": ORIGINATING_SUMMONS_AND_AFFIDAVIT,
    "Trespass/Eviction": PLAINT_AND_VERIFYING_AFFIDAVIT,
    "Boundary/Title Dispute": PLAINT_AND_VERIFYING_AFFIDAVIT,
    "Procedural Application": NOTICE_OF_MOTION_AND_AFFIDAVIT,
}

SUBCATEGORY_ALIASES = {
    "Boundary Dispute": "Boundary/Title Dispute",
    "Title Dispute": "Boundary/Title Dispute",
}


def canonical_subcategory(subcategory: str | None) -> str:
    value = subcategory or "Temporary Injunction"
    return SUBCATEGORY_ALIASES.get(value, value)


def default_pleading_type(subcategory: str | None) -> str:
    resolved_subcategory = canonical_subcategory(subcategory)
    return DEFAULT_PLEADING_TYPE_BY_SUBCATEGORY.get(
        resolved_subcategory, NOTICE_OF_MOTION_AND_AFFIDAVIT
    )


def drafting_packet_for(
    *,
    subcategory: str | None,
    pleading_type: str | None = None,
) -> DraftingPacket | None:
    resolved_subcategory = canonical_subcategory(subcategory)
    resolved_pleading_type = pleading_type or default_pleading_type(resolved_subcategory)
    return _PACKETS_BY_KEY.get((resolved_subcategory, resolved_pleading_type))


def supported_subcategories() -> set[str]:
    return set(DEFAULT_PLEADING_TYPE_BY_SUBCATEGORY)
