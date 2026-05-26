from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DraftDocumentSpec:
    document_type: str
    title: str
    activity_title: str
    instruction: str
    required: bool = True


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
        DraftDocumentSpec(
            document_type="injunction_certificate_of_urgency",
            title="Certificate of Urgency",
            activity_title="Drafting Certificate of Urgency",
            instruction=(
                "Draft a Certificate of Urgency for the temporary injunction application. "
                "Use only facts showing immediate risk or irreparable harm, identify why "
                "ordinary scheduling is inadequate, and avoid exaggerating urgency beyond "
                "the masked facts."
            ),
            required=False,
        ),
        DraftDocumentSpec(
            document_type="injunction_draft_order",
            title="Draft Order for Temporary Injunction",
            activity_title="Drafting Draft Order",
            instruction=(
                "Draft a concise Draft Order for the temporary injunction application. "
                "Mirror the prayers sought in the Notice of Motion, preserve clear party "
                "obligations, and avoid adding relief not supported by the masked facts."
            ),
            required=False,
        ),
        DraftDocumentSpec(
            document_type="injunction_written_submissions",
            title="Written Submissions on Temporary Injunction",
            activity_title="Drafting Written Submissions",
            instruction=(
                "Draft short written submissions for the temporary injunction application. "
                "Organize the argument around the applicable Kenyan injunction principles, "
                "connect each issue to the masked facts, and cite retrieved authorities only."
            ),
            required=False,
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
        DraftDocumentSpec(
            document_type="adverse_possession_draft_order",
            title="Draft Order for Adverse Possession",
            activity_title="Drafting Draft Order",
            instruction=(
                "Draft a Draft Order for the adverse possession summons. Keep the orders "
                "aligned to the questions and relief in the Originating Summons, and do "
                "not add land registration directions unsupported by the masked facts."
            ),
            required=False,
        ),
        DraftDocumentSpec(
            document_type="adverse_possession_written_submissions",
            title="Written Submissions on Adverse Possession",
            activity_title="Drafting Written Submissions",
            instruction=(
                "Draft written submissions for adverse possession. Address possession, "
                "continuity, openness, exclusivity, interruption, and the statutory period "
                "using the masked facts and retrieved Kenyan authorities."
            ),
            required=False,
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
        DraftDocumentSpec(
            document_type="trespass_witness_statement",
            title="Witness Statement",
            activity_title="Drafting Witness Statement",
            instruction=(
                "Draft a factual witness statement for the trespass or eviction claim. "
                "Use first-person chronology, preserve anonymized names and land references, "
                "and avoid legal argument or unsupported valuation details."
            ),
            required=False,
        ),
        DraftDocumentSpec(
            document_type="trespass_list_of_documents",
            title="List of Documents",
            activity_title="Drafting List of Documents",
            instruction=(
                "Draft a List of Documents for the trespass or eviction claim. Include "
                "only document categories or exhibits clearly supported by the masked facts, "
                "and mark uncertain items as subject to advocate confirmation."
            ),
            required=False,
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
        DraftDocumentSpec(
            document_type="boundary_title_witness_statement",
            title="Witness Statement",
            activity_title="Drafting Witness Statement",
            instruction=(
                "Draft a factual witness statement for the boundary or title dispute. "
                "Keep the account neutral on disputed ownership, preserve the chronology, "
                "and avoid inventing survey or registry evidence."
            ),
            required=False,
        ),
        DraftDocumentSpec(
            document_type="boundary_title_list_of_documents",
            title="List of Documents",
            activity_title="Drafting List of Documents",
            instruction=(
                "Draft a List of Documents for the boundary or title dispute. Include "
                "only title, survey, registry, correspondence, or occupation evidence "
                "that is supported by the masked facts."
            ),
            required=False,
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
        DraftDocumentSpec(
            document_type="procedural_draft_order",
            title="Draft Order for Procedural Relief",
            activity_title="Drafting Draft Order",
            instruction=(
                "Draft a Draft Order for the procedural application. Mirror the procedural "
                "relief sought, keep deadlines and obligations clear, and avoid adding "
                "orders not supported by the masked facts."
            ),
            required=False,
        ),
        DraftDocumentSpec(
            document_type="procedural_written_submissions",
            title="Written Submissions on Procedural Relief",
            activity_title="Drafting Written Submissions",
            instruction=(
                "Draft concise written submissions for the procedural application. Tie "
                "the procedural history to the requested relief and retrieved Kenyan "
                "authorities without arguing unsupported merits."
            ),
            required=False,
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
            DraftDocumentSpec(
                document_type="trespass_application_draft_order",
                title="Draft Order for Trespass or Eviction Relief",
                activity_title="Drafting Draft Order",
                instruction=(
                    "Draft a Draft Order for the trespass or eviction application. "
                    "Mirror the interim prayers, keep obligations clear, and avoid "
                    "final eviction relief unless the masked facts and application type support it."
                ),
                required=False,
            ),
            DraftDocumentSpec(
                document_type="trespass_application_written_submissions",
                title="Written Submissions on Trespass or Eviction Relief",
                activity_title="Drafting Written Submissions",
                instruction=(
                    "Draft concise written submissions for the trespass or eviction "
                    "application. Connect the interim relief sought to the masked facts "
                    "and retrieved Kenyan authorities."
                ),
                required=False,
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
            DraftDocumentSpec(
                document_type="boundary_title_application_draft_order",
                title="Draft Order for Boundary or Title Preservation",
                activity_title="Drafting Draft Order",
                instruction=(
                    "Draft a Draft Order for the boundary or title preservation application. "
                    "Mirror the preservation prayers and avoid resolving ownership or survey "
                    "issues not proved by the masked facts."
                ),
                required=False,
            ),
            DraftDocumentSpec(
                document_type="boundary_title_application_written_submissions",
                title="Written Submissions on Boundary or Title Preservation",
                activity_title="Drafting Written Submissions",
                instruction=(
                    "Draft concise written submissions for the preservation application. "
                    "Tie the need for interim preservation to the masked facts and retrieved "
                    "Kenyan authorities."
                ),
                required=False,
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


def selected_document_specs(
    packet: DraftingPacket,
    selected_document_types: list[str] | None,
) -> tuple[DraftDocumentSpec, ...]:
    if not selected_document_types:
        return tuple(spec for spec in packet.documents if spec.required)

    selected = set(selected_document_types)
    required_types = {spec.document_type for spec in packet.documents if spec.required}
    selected.update(required_types)
    return tuple(spec for spec in packet.documents if spec.document_type in selected)


def unsupported_document_types(
    packet: DraftingPacket,
    selected_document_types: list[str] | None,
) -> set[str]:
    if not selected_document_types:
        return set()
    available = {spec.document_type for spec in packet.documents}
    return set(selected_document_types) - available


def supported_subcategories() -> set[str]:
    return set(DEFAULT_PLEADING_TYPE_BY_SUBCATEGORY)
