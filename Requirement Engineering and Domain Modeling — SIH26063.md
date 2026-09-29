# Requirement Engineering and Domain Modeling Report

## SIH Problem Statement

**Problem Statement ID:** SIH26063  
**Title:** Integrated Polar Science Outreach, Knowledge Repository and Media Dissemination Portal  
**Organization:** Ministry of Earth Sciences (MoES)  
**Department:** National Centre for Polar and Ocean Research (NCPOR)  
**Category:** Software  
**Theme:** Smart Education

The official problem statement asks for a comprehensive outreach portal capable of archiving expedition reports, scientific datasets, publications, photographs, videos and institutional activities, while also supporting generation of content for websites and social media.

NCPOR already maintains digital information resources, including an online library containing publications and expedition reports and an Indian Antarctic Expedition Directory. Therefore, the proposed system is designed not merely as another digital archive but as an integrated **knowledge-to-outreach workflow** over such resources.

---

# 1. Introduction

NCPOR generates and maintains a large amount of scientific information related to polar and ocean research. This information may exist in different formats, including:

- Expedition reports
- Scientific publications
- Research datasets
- Photographs
- Videos
- Institutional activity records
- Reports and supporting media

Although these resources may individually be available digitally, converting scientific material into accessible public outreach content requires several separate activities:

**Find source → understand source → identify useful evidence → create content → verify facts → approve → publish → maintain**

The proposed platform integrates this complete workflow into a single system.

---

# 2. Problem Definition

## 2.1 Existing Situation

NCPOR already provides digital resources such as its online library and Polar Directory.

The core problem is therefore not simply:

> “How do we store NCPOR documents?”

Instead, the system addresses:

> **How can heterogeneous polar-science resources be organized, discovered, transformed into evidence-backed public communication, reviewed, published and kept synchronized with changing scientific sources?**

The current outreach process can potentially require researchers or communication personnel to manually:

1. Find relevant reports.
2. Search long PDFs.
3. identify useful passages.
4. verify dates, numbers and scientific statements.
5. rewrite technical information for the public.
6. retain references to the original material.
7. obtain approval.
8. update previously published material when source information changes.

The proposed platform integrates these activities.

---

# 3. Proposed Solution

The proposed solution is an:

## **Evidence-Linked Polar Knowledge and Outreach Platform**

The system contains six major user-facing modules:

1. **Knowledge Repository**
2. **Document Upload and Processing**
3. **Intelligent Search**
4. **AI-Assisted Outreach Editor**
5. **Evidence-Based Review and Approval**
6. **Published Content and Source-Update Monitoring**

Module 6 is the primary differentiator: it aligns evidence across source versions, classifies what changed, propagates the impact to dependent claims and publications, and creates targeted human re-verification tasks (FR-36 to FR-43).

The overall information flow is:

**NCPOR Sources**

↓  

**Ingestion & Metadata**

↓  

**Document Processing**

↓  

**Searchable Knowledge Repository**

↓  

**Hybrid Retrieval**

↓  

**Evidence Passages**

↓  

**AI-Assisted Content Generation**

↓  

**Claim ↔ Evidence Linking**

↓  

**Human Review**

↓  

**Approved Content**

↓  

**Publication**

↓  

**Source Change Detection**

↓  

**Affected Content Review**

---

# 4. Requirement Engineering

## 4.1 Requirement Engineering Objective

Requirement engineering is performed to identify:

- What the system must accomplish.
- Who will interact with the system.
- What information must be maintained.
- What restrictions apply.
- How success will be measured.
- Which features come directly from the SIH problem statement.
- Which features are enhancements proposed by the team.

The requirements in this report are currently derived from:

1. The SIH26063 problem statement.
2. Publicly visible NCPOR resources.
3. Analysis of the proposed workflow.

Requirements involving internal NCPOR processes, permissions or publication policies must ultimately be validated with the problem-statement owner.

---

# 5. Stakeholder Analysis

## 5.1 Primary Stakeholders

### 1. NCPOR Administrator / Archivist

Responsible for maintaining institutional resources.

Needs to:

- Upload resources.
- Enter metadata.
- Correct metadata.
- Manage access.
- Maintain document versions.
- Organize collections.

---

### 2. Researcher / Scientist

Provides or consumes scientific resources.

Needs to:

- Search scientific information.
- Retrieve original documents.
- Locate specific evidence.
- Verify scientific information.
- Contribute resources where permitted.

---

### 3. Outreach / Content Creator

Responsible for transforming scientific information into understandable public communication.

Needs to:

- Discover relevant material.
- Generate outreach drafts.
- See evidence associated with generated statements.
- Edit generated content.
- Submit drafts for review.

---

### 4. Reviewer / Approver

Responsible for ensuring scientific and editorial quality.

Needs to:

- Review submitted drafts.
- Inspect each factual claim.
- Open supporting evidence.
- Request corrections.
- Approve a specific revision.

---

### 5. Public User

Examples include:

- Students
- Teachers
- Researchers
- Journalists
- General public

Needs to:

- Browse approved public resources.
- Search available material.
- Read approved outreach content.
- Access permitted downloads.

---

### 6. System Administrator

Responsible for technical operation.

Needs to:

- Manage user roles.
- Configure permissions.
- Maintain services.
- Monitor processing failures.
- Configure models/providers where applicable.

---

# 6. Functional Requirements

Requirements are identified using the format:

**FR-XX**

Priority:

- **M — Must Have**
- **S — Should Have**
- **C — Could Have**

---

## FR-01 — User Authentication

**Priority:** M

The system shall authenticate authorized internal users.

Possible roles include:

- Administrator
- Archivist
- Researcher
- Content Creator
- Reviewer

---

## FR-02 — Role-Based Authorization

**Priority:** M

The system shall restrict functions according to user roles.

For example:

**Content Creator**

Can create and edit drafts but cannot approve them.

**Reviewer**

Can review and approve submitted drafts.

**Administrator**

Can configure resources and permissions.

---

## FR-03 — Asset Upload

**Priority:** M

Authorized users shall be able to upload resources such as:

- PDF documents
- Images
- Videos
- Dataset files
- Institutional activity records

---

## FR-04 — Metadata Management

**Priority:** M

Each asset shall contain structured metadata.

Example metadata:

- Title
- Description
- Asset type
- Expedition
- Year
- Station
- Author/contributor
- Keywords
- Attribution
- Access level
- Upload date
- Source

---

## FR-05 — Asset Classification

**Priority:** M

The system shall organize assets according to attributes such as:

- Topic
- Expedition
- Station
- Year
- Format

---

## FR-06 — Document Processing

**Priority:** M

Uploaded documents shall be processed automatically.

For PDFs, the system should extract:

- Text
- Page boundaries
- Headings where available
- Tables where applicable
- OCR text for scanned documents

The original uploaded document must remain preserved.

---

## FR-07 — Image Management

**Priority:** S

The system shall support:

- Image preview
- Caption
- Attribution
- Metadata
- Searchable tags

---

## FR-08 — Video Management

**Priority:** S

The system shall support:

- Video playback
- Transcript storage
- Transcript search
- Timestamp-linked evidence

---

## FR-09 — Dataset Management

**Priority:** S

The system shall preserve original dataset files.

For supported tabular formats, it should provide:

- Preview
- Column information
- Basic metadata
- Dataset search

---

## FR-10 — Keyword Search

**Priority:** M

Users shall be able to search resources using keywords.

Search results shall expose the source from which the result originated.

---

## FR-11 — Semantic Search

**Priority:** M

The system shall support semantic similarity search to retrieve relevant evidence even when the user's query does not exactly match the wording of a source.

---

## FR-12 — Search Filtering

**Priority:** M

Users shall be able to filter results using fields such as:

- Expedition
- Station
- Year
- Asset type
- Topic
- Access level

---

## FR-13 — Evidence-Level Retrieval

**Priority:** M

The system shall return evidence at an appropriate source location rather than only returning entire documents.

For example:

**PDF**

Document + page + passage

**Video**

Video + timestamp interval + transcript

**Dataset**

Dataset + table/column/row reference where practical

---

## FR-14 — Source Navigation

**Priority:** M

Selecting evidence shall take the user to the corresponding location in the original source whenever technically possible.

Example:

Search result  
→ Expedition Report  
→ Page 37  
→ Relevant passage highlighted

---

# 7. AI-Assisted Outreach Requirements

## FR-15 — Outreach Content Generation

**Priority:** M

Authorized users shall be able to create outreach drafts using retrieved material.

Initially supported formats:

1. Website article
2. Social-media post

---

## FR-16 — Audience Selection

**Priority:** S

The content creator shall be able to specify the intended audience.

Examples:

- School students
- General public
- Scientific audience

The generated style should adapt accordingly without changing the underlying factual evidence.

---

## FR-17 — Evidence-Grounded Generation

**Priority:** M

Generated factual statements should be based on evidence retrieved from the repository.

The generation service should return structured information such as:

- Draft text
- Factual claims
- Supporting evidence IDs
- Unresolved questions
- Missing evidence

---

## FR-18 — Evidence ID Validation

**Priority:** M

The backend shall verify that every evidence identifier supplied by the generation layer actually exists.

A nonexistent evidence ID shall be rejected.

Important:

**Existence validation does not imply scientific correctness.**

Human review remains necessary to determine whether the evidence actually supports the generated claim.

---

## FR-19 — Claim-Evidence Mapping

**Priority:** M

The system shall maintain an explicit relationship:

**Draft Revision → Claim → Evidence**

Example:

> “India's 42nd Antarctic expedition commenced in …”

↓

Claim ID: C104

↓

Evidence ID: E653

↓

Report X, Version 2, Page 16

This makes generated content traceable.

---

# 8. Review and Approval Requirements

## FR-20 — Draft Versioning

**Priority:** M

Every meaningful revision of outreach content shall be stored as a separate draft revision.

---

## FR-21 — Review Submission

**Priority:** M

Content creators shall be able to submit a draft revision for review.

---

## FR-22 — Evidence Review Interface

**Priority:** M

Reviewers shall be able to inspect:

**Claim**

alongside

**Supporting Evidence**

without manually searching for the original source.

---

## FR-23 — Review Decision

**Priority:** M

Reviewer actions shall include:

- Approve
- Request changes

Optional implementation:

- Add review comments

---

## FR-24 — Revision-Specific Approval

**Priority:** M

Approval shall apply to a particular draft revision.

If an approved draft is modified afterward:

**Approved Revision 3**

→ edit

→ **Revision 4 — Review Required**

It must not inherit Revision 3's approval automatically.

---

## FR-25 — Basic Consistency Checks

**Priority:** S

The system should identify suspicious inconsistencies involving:

- Numbers
- Units
- Dates
- Locations

These results shall be presented as warnings rather than definitive errors.

---

# 9. Publication Requirements

## FR-26 — Publication

**Priority:** M

Only approved draft revisions shall be eligible for publication through the platform.

---

## FR-27 — Published Content Repository

**Priority:** M

The system shall maintain approved/public outreach material separately from editable drafts.

---

## FR-28 — Social-Media Export

**Priority:** M for MVP

Approved social-media content shall initially support:

- Copy
- Download/export

Direct API integration with social-media platforms is not necessary for the first version.

---

# 10. Proposed Differentiating Requirement

## Source-Aware Content Lifecycle

This section represents a **team-proposed enhancement**, rather than wording explicitly required by the SIH statement.

It is designed to solve an important long-term problem:

> What happens to public outreach content when the scientific source from which it was created changes?

---

## FR-29 — Immutable Source Versions

**Priority:** M for proposed differentiator

Every processed source shall have a version.

Instead of replacing:

**ExpeditionReport.pdf**

the system stores:

**Asset**

→ Version 1  
→ Version 2  
→ Version 3

Previous versions remain available for traceability.

---

## FR-30 — File Fingerprinting

**Priority:** M

Each source version shall maintain a cryptographic file hash or equivalent fingerprint so that changed files can be detected reliably.

---

## FR-31 — Source Change Detection

**Priority:** M

When a new version of an existing source is uploaded, the system shall determine that the source has changed.

---

## FR-32 — Impact Analysis

**Priority:** M

The system shall identify:

**Evidence**

linked to the previous source version

↓

**Claims**

using that evidence

↓

**Drafts / Published Content**

containing those claims

---

## FR-33 — Review Required Flag

**Priority:** M

Affected published content shall be marked:

**Source Updated — Review Required**

without automatically declaring the existing content false.

---

## FR-34 — Source Comparison

**Priority:** S

Reviewers should be able to compare:

**Old Evidence**

with

**New Evidence**

before deciding whether content must be updated.

---

## FR-35 — Fine-Grained Change Detection

**Priority:** C / Advanced

After the document-level workflow works correctly, the system may detect changes at:

- Section
- Paragraph
- Evidence-passage

level.

This can reduce unnecessary review notifications.

---

## FR-36 — Evidence Alignment

**Priority:** M for proposed differentiator

When a new source version is ingested, the system shall attempt to map `EvidencePassage` records from the previous version to corresponding records in the new version.

An unmapped passage shall be recorded as unmatched rather than discarded.

> Naming note: the team's novelty document calls this entity `EvidenceUnit`. This report uses `EvidencePassage` as the canonical name; the two are synonymous.

---

## FR-37 — Evidence Change Classification

**Priority:** M for proposed differentiator

The system shall classify each mapped passage as one of:

- **UNCHANGED** — repositioned or reworded with preserved meaning
- **TEXT_REPHRASED** — wording changed, meaning likely preserved
- **NUMERIC_CHANGED** — a numeric value differs (for example 4.7 → 4.3)
- **DATE_CHANGED** — a date or year differs
- **LOCATION_CHANGED** — station, region or coordinate differs
- **QUALIFIER_CHANGED** — modality or strength changed (for example "may" → "will")
- **EVIDENCE_REMOVED** — supporting passage deleted in the new version
- **CONTRADICTION** — new evidence conflicts with existing support
- **NEW_EVIDENCE** — relevant passage added in the new version

Classification results shall be stored as structured data, not free text.

---

## FR-38 — Claim Impact Propagation

**Priority:** M for proposed differentiator

When supporting evidence changes, the system shall identify every `Claim` dependent on that evidence by traversing `EvidencePassage → EvidenceLink → Claim`.

---

## FR-39 — Publication Impact Propagation

**Priority:** M for proposed differentiator

The system shall identify every `DraftRevision` and `Publication` containing an affected `Claim` by traversing `Claim → DraftRevision → Publication`.

---

## FR-40 — Evidence Conflict Detection

**Priority:** S

Where permitted sources materially disagree about a claim, the system shall expose the conflict to the reviewer instead of silently selecting the most semantically similar passage.

---

## FR-41 — Insufficient Evidence Handling

**Priority:** M

The generation workflow shall be able to return **INSUFFICIENT_EVIDENCE** rather than forcing a content answer.

A returned `INSUFFICIENT_EVIDENCE` result shall not be attached to any fabricated evidence identifier.

---

## FR-42 — Re-verification Workflow

**Priority:** M for proposed differentiator

A published artifact whose supporting evidence materially changes shall enter a human re-verification workflow through a `ReviewTask`, without being automatically rewritten, retracted or declared false.

---

## FR-43 — Historical Traceability

**Priority:** M for proposed differentiator

The system shall preserve the exact source version and evidence mapping used when a published revision was approved, so that an approval can be reconstructed after later source changes.

---

# 11. Non-Functional Requirements

## NFR-01 — Usability

The main functions shall be understandable to users without specialist AI knowledge.

Users should be able to:

**Search → inspect → generate → verify → approve**

through a consistent interface.

---

## NFR-02 — Performance

For the hackathon prototype:

- Normal metadata operations should respond interactively.
- Typical search queries should return results within a few seconds under demonstration-scale load.
- Long document processing shall occur asynchronously.

Exact production limits must be determined after NCPOR workload requirements are known.

---

## NFR-03 — Reliability

Processing failure shall not corrupt the original uploaded resource.

Failed processing jobs must be identifiable and retryable.

---

## NFR-04 — Traceability

Every published factual claim created through the generation workflow should be traceable to:

**Publication**

→ Draft Revision  
→ Claim  
→ Evidence  
→ Asset Version  
→ Original Asset

---

## NFR-05 — Data Integrity

Original uploaded resources and historical source versions shall not be silently overwritten.

---

## NFR-06 — Security

The system shall implement:

- Authentication
- Authorization
- Role-based access control
- Input validation
- Secure file handling
- Protection of restricted resources

---

## NFR-07 — Auditability

Important actions should be logged, including:

- Upload
- New source version
- Draft submission
- Approval
- Rejection/change request
- Publication

---

## NFR-08 — Scalability

The architecture should allow additional:

- Asset types
- Collections
- Users
- Documents
- Embedding models
- Generation models

without redesigning the entire platform.

---

## NFR-09 — Maintainability

Repository, retrieval, generation, review and publication functions should remain logically modular.

---

## NFR-10 — Explainability

AI-generated outputs shall expose their supporting sources instead of presenting generated claims as unsupported answers.

---

# 12. Business Rules

### BR-01
Every asset must have at least one version.

### BR-02
An AssetVersion belongs to exactly one Asset.

### BR-03
An Evidence Passage must originate from a specific AssetVersion.

### BR-04
A factual Claim may reference one or more Evidence Passages.

### BR-05
A Draft may contain multiple revisions.

### BR-06
Only a submitted DraftRevision can undergo formal review.

### BR-07
Approval belongs to a specific DraftRevision.

### BR-08
Editing approved content creates a new revision requiring approval.

### BR-09
Only an approved revision may become an approved publication through the managed workflow.

### BR-10
Historical source versions must remain accessible internally for traceability.

### BR-11
Updating a source must not silently rewrite old evidence references.

### BR-12
A changed source does not automatically mean that every linked claim is incorrect.

It means:

**Review may be required.**

### BR-13

Evidence from a previous source version shall never be silently remapped to a new version. Mapping is an explicit, recorded action (FR-36).

### BR-14

Every `EvidenceDelta` shall resolve to exactly one change class from FR-37. Unclassified deltas shall be treated as material until a human decides otherwise.

### BR-15

An `ImpactRecord` shall be created for every claim reachable from a material `EvidenceDelta`. Impact analysis shall not overwrite prior `ImpactRecord` entries.

### BR-16

Only a human `ReviewTask` outcome may move a claim out of `RECHECK_REQUIRED`. Automated detection may only set review states, never clear them.

### BR-17

A claim in `UNSUPPORTED` or `CONFLICT` state shall not be published as a factual assertion.

### BR-18

The verification state of a claim at approval time shall be preserved with the approved `DraftRevision` (FR-43), even if the claim's state changes later.

---

# 13. System Constraints

## Technical Constraints

- Heterogeneous input formats.
- OCR quality can vary for scanned reports.
- Semantic retrieval may occasionally retrieve irrelevant passages.
- Generative AI can produce unsupported statements.
- Dataset structures may vary substantially.
- Video transcripts may not always be available.

Therefore, AI output must remain reviewable rather than being treated as automatically correct.

---

## Organizational Constraints

Actual:

- Access-control policies
- Publication permissions
- Source ownership
- Review hierarchy
- Internal user roles

must be confirmed with NCPOR before production deployment.

---

## Content Constraints

The system must respect:

- Attribution
- Asset permissions
- Applicable copyright/reuse restrictions
- Restricted institutional information

No assumption should be made that every resource available on an existing website can automatically be republished elsewhere.

---

# 14. Assumptions

For prototype development, the following assumptions are made:

**A1.** NCPOR can provide or authorize a limited test collection.

**A2.** Users have identifiable roles.

**A3.** Public and internal resources can be distinguished.

**A4.** Outreach content requires human approval.

**A5.** Most reports can be converted into searchable text through direct extraction or OCR.

**A6.** AI-generated outreach content is treated as a draft rather than automatically published information.

These assumptions require stakeholder validation before production use.

---

# 15. Use Cases

# UC-01 — Upload Resource

**Primary Actor:** Archivist

### Preconditions

- User is authenticated.
- User has upload permission.

### Main Flow

1. User selects Upload.
2. User selects file.
3. User enters metadata.
4. System validates file.
5. Original resource is stored.
6. AssetVersion is created.
7. Processing job begins.
8. Text/media information is extracted.
9. Evidence units are generated.
10. Asset becomes searchable.

### Postcondition

Resource is available according to its access policy.

---

# UC-02 — Search Knowledge Repository

**Primary Actor:** Researcher / Content Creator

### Main Flow

1. User enters query.
2. User optionally selects filters.
3. System applies access restrictions.
4. Keyword retrieval is executed.
5. Semantic retrieval is executed.
6. Results are combined/ranked.
7. Evidence passages are displayed.
8. User opens source location.

### Postcondition

User can verify the retrieved information directly against its source.

---

# UC-03 — Generate Outreach Content

**Primary Actor:** Content Creator

### Main Flow

1. User selects topic.
2. Relevant evidence is retrieved.
3. User chooses content type.
4. User selects target audience.
5. Generation component produces structured draft.
6. Claims are linked to evidence IDs.
7. Backend validates evidence references.
8. Draft revision is stored.
9. User edits draft if necessary.

---

# UC-04 — Review Draft

**Primary Actor:** Reviewer

### Main Flow

1. Reviewer opens review queue.
2. Reviewer selects submitted draft.
3. System displays draft and claim-evidence mappings.
4. Reviewer examines evidence.
5. Reviewer checks flagged inconsistencies.
6. Reviewer either:

**Approve**

or

**Request Changes**

7. Decision is stored against that revision.

---

# UC-05 — Publish Approved Content

**Primary Actor:** Authorized Publisher/Reviewer

### Preconditions

Draft revision is approved.

### Main Flow

1. User selects approved revision.
2. System verifies approval.
3. Approved content becomes a publication.
4. Publication retains links to the supporting claims and evidence.

---

# UC-06 — Update Existing Source

**Primary Actor:** Archivist

### Main Flow

1. Archivist uploads revised source.
2. System identifies existing asset.
3. New AssetVersion is created.
4. Old AssetVersion is preserved.
5. File fingerprint is compared.
6. New version is processed.
7. System aligns previous-version evidence to new-version evidence (FR-36).
8. EvidenceDelta records are created and classified (FR-37).
9. Material deltas are traversed to related claims (FR-38).
10. Related publications are identified (FR-39).
11. ImpactRecord rows and ReviewTask items are created (FR-42).
12. Affected claims are set to `RECHECK_REQUIRED`; content is marked **Source Updated — Review Required**.

### Alternative Flow — unchanged file

If the fingerprint matches an existing version, no new `AssetVersion`, delta or review task is created.

---

# UC-07 — Review Source Change

**Primary Actor:** Reviewer

### Preconditions

A `ReviewTask` of type `SOURCE_CHANGE_REVERIFICATION` exists.

### Main Flow

1. Reviewer opens the re-verification queue.
2. System displays affected publication and `ImpactRecord`.
3. System displays the `EvidenceDelta` with its change class.
4. System displays previous evidence and updated evidence side by side.
5. Reviewer determines whether the claim remains valid.
6. Reviewer records an outcome on the `ReviewTask`:

- **CONFIRMED** — claim stays, returns to `SUPPORTED`
- **REVISED** — claim text edited, creating a new `DraftRevision` requiring approval
- **RETIRED** — claim or publication withdrawn

7. The outcome is stored against the task and the claim's `verificationStatus` is updated.

---

# UC-08 — Abstain for Missing Evidence

**Primary Actor:** Content Creator

### Main Flow

1. User requests generation for a topic.
2. Retrieval finds no evidence above threshold for the requested claim.
3. System returns `INSUFFICIENT_EVIDENCE` (FR-41).
4. No draft claim is created and no evidence identifier is fabricated.
5. User is directed to upload or request relevant source material.

---

# 16. System Context Model

The system boundary can be represented as:

```text
                        ┌──────────────────────┐
                        │     Public User      │
                        └──────────┬───────────┘
                                   │
                                   ▼
┌─────────────┐          ┌───────────────────────────────┐
│ Researcher  │─────────▶│                               │
└─────────────┘          │   POLAR KNOWLEDGE & OUTREACH │
                         │            SYSTEM             │
┌─────────────┐          │                               │
│ Archivist   │─────────▶│ Repository                    │
└─────────────┘          │ Search                        │
                         │ Generation                    │
┌─────────────┐          │ Review                        │
│ Content     │─────────▶│ Publication                   │
│ Creator     │          │ Version Tracking              │
└─────────────┘          │                               │
                         └───────────────┬───────────────┘
┌─────────────┐                          │
│ Reviewer    │─────────────────────────▶│
└─────────────┘                          │
                                        ▼
                              ┌──────────────────────┐
                              │ Document Processing  │
                              │ Retrieval / AI       │
                              │ File Storage / DB    │
                              └──────────────────────┘
```

---

# 17. Domain Modeling

The most important part of the domain model is preserving the chain:

**Asset → Version → Evidence → Claim → Draft Revision → Review → Publication**

When a source later changes, the chain extends:

**Publication → EvidenceDelta → ImpactRecord → ReviewTask**

This chain provides provenance and traceability in both directions: backwards to origin, and forwards to re-verification.

---

# 18. Core Domain Entities

## 18.1 User

Represents an authenticated system user.

### Attributes

- userId
- name
- email
- status

### Relationships

User has one or more Roles.

User may:

- Upload assets
- Create drafts
- Submit reviews
- Approve content

---

## 18.2 Role

Defines permissions.

Examples:

- ADMIN
- ARCHIVIST
- RESEARCHER
- CONTENT_CREATOR
- REVIEWER

### Attributes

- roleId
- roleName

---

## 18.3 Asset

Represents the logical scientific/institutional resource.

Examples:

- Expedition report
- Photograph
- Dataset
- Video
- Publication

### Attributes

- assetId
- title
- description
- assetType
- accessLevel
- createdAt

An Asset is independent of its physical versions.

---

## 18.4 AssetVersion

Represents a particular version of an Asset.

### Attributes

- versionId
- versionNumber
- filePath
- fileHash
- uploadedAt
- processingStatus

### Relationship

**Asset 1 : N AssetVersion**

Example:

```text
Expedition Report
    |
    +-- Version 1
    |
    +-- Version 2
    |
    +-- Version 3
```

---

## 18.5 Metadata

Contains descriptive information associated with resources.

Examples:

- Year
- Expedition
- Station
- Topic
- Attribution
- Contributor

---

## 18.6 Expedition

Represents a polar expedition.

### Attributes

- expeditionId
- name
- year
- description

One expedition may contain many Assets.

---

## 18.7 Station

Represents a research station/location associated with content.

### Attributes

- stationId
- name
- region

---

## 18.8 EvidencePassage

One of the most important entities.

It represents a retrievable portion of an AssetVersion.

### Attributes

- evidenceId
- content
- locationType
- pageNumber
- startTimestamp
- endTimestamp
- embedding
- sequenceNumber

Possible evidence locations:

**PDF**

Page 15

**Video**

00:04:21–00:04:45

**Dataset**

Table 2 → Column Temperature → Row 19

> Alias: the novelty and differentiation document calls this entity `EvidenceUnit`. See §18.19.

---

## 18.9 Draft

Represents one outreach-content project.

### Attributes

- draftId
- title
- contentType
- targetAudience
- status
- createdBy
- createdAt

---

## 18.10 DraftRevision

Stores a specific version of a Draft.

### Attributes

- revisionId
- revisionNumber
- content
- createdAt

### Relationship

**Draft 1 : N DraftRevision**

---

## 18.11 Claim

Represents an individual factual statement appearing in a DraftRevision.

### Attributes

- claimId
- claimText
- claimType
- verificationStatus
- statusChangedAt
- statusReason

### Verification States

- **SUPPORTED** — linked evidence exists and has not changed since approval
- **RECHECK_REQUIRED** — supporting evidence materially changed
- **NEEDS_REVISION** — reviewer determined the wording must change
- **UNSUPPORTED** — no sufficient evidence could be linked
- **CONFLICT** — permitted sources materially disagree

A source update changes the state of dependent claims. It does not automatically rewrite or delete public content.

See §22.2 for the state model.

Example:

```text
Claim:
"The expedition collected samples from X location in 2025."
```

---

## 18.12 EvidenceLink

Associative entity linking Claims with EvidencePassages.

### Attributes

- evidenceLinkId
- claimId
- evidenceId

The relationship is:

**Claim N : M EvidencePassage**

because:

- One claim may require multiple pieces of evidence.
- One evidence passage may support several claims.

---

## 18.13 Review

Represents the review of one DraftRevision.

### Attributes

- reviewId
- status
- reviewerId
- comment
- reviewedAt

Possible status:

- PENDING
- CHANGES_REQUESTED
- APPROVED

---

## 18.14 Publication

Represents approved published outreach material.

### Attributes

- publicationId
- revisionId
- publishedAt
- publicationStatus

Possible states:

- PUBLISHED
- REVIEW_REQUIRED
- ARCHIVED

---

## 18.15 SourceChangeEvent

Represents detection of a new source version.

### Attributes

- changeId
- oldVersionId
- newVersionId
- detectedAt
- processingStatus

This drives impact analysis.

---

## 18.16 EvidenceDelta

Represents the aligned difference between one `EvidencePassage` in a previous `AssetVersion` and its counterpart in a new `AssetVersion`.

### Attributes

- deltaId
- oldVersionId
- newVersionId
- oldEvidenceId
- newEvidenceId
- changeClass
- changeDetail
- materiality
- detectedAt

### changeClass Values

See FR-37.

### Relationship

A `SourceChangeEvent` produces zero or more `EvidenceDelta` records.

An `EvidenceDelta` belongs to exactly one `SourceChangeEvent`.

---

## 18.17 ImpactRecord

Records that a given Claim or Publication is affected by an `EvidenceDelta`.

### Attributes

- impactRecordId
- deltaId
- claimId
- publicationId
- impactStatus
- createdAt
- resolvedAt

### impactStatus Values

- OPEN
- ACKNOWLEDGED
- RESOLVED
- DISMISSED

---

## 18.18 ReviewTask

A human verification task created either by content submission or by a detected source change.

### Attributes

- taskId
- taskType
- claimId
- publicationId
- deltaId
- assignedTo
- status
- outcome
- comment
- createdAt
- completedAt

### taskType Values

- SUBMISSION_REVIEW
- SOURCE_CHANGE_REVERIFICATION

### outcome Values

- CONFIRMED
- REVISED
- RETIRED

---

## 18.19 Naming Reconciliation

The team's novelty and differentiation document uses slightly different names for two entities. This report's names are canonical; the alternatives are listed so both documents remain readable together.

| This report | Novelty document |
|---|---|
| EvidencePassage | EvidenceUnit |
| Claim | ScientificClaim |
| SourceChangeEvent + EvidenceDelta | EvidenceDelta |
| Review | ReviewTask |

---

# 19. Domain Class Diagram

```text
┌──────────────┐
│     User     │
├──────────────┤
│ userId       │
│ name         │
│ email        │
└──────┬───────┘
       │ N:M
       ▼
┌──────────────┐
│     Role     │
└──────────────┘


┌──────────────────┐
│      Asset       │
├──────────────────┤
│ assetId          │
│ title            │
│ type             │
│ accessLevel      │
└────────┬─────────┘
         │ 1
         │
         │ N
         ▼
┌──────────────────┐
│   AssetVersion   │
├──────────────────┤
│ versionId        │
│ versionNumber    │
│ fileHash         │
│ filePath         │
└────────┬─────────┘
         │ 1
         │
         │ N
         ▼
┌──────────────────┐
│ EvidencePassage  │
├──────────────────┤
│ evidenceId       │
│ content          │
│ page/timestamp   │
│ embedding        │
└────────┬─────────┘
         │
         │ N
         │
         │ N
┌────────▼─────────┐
│   EvidenceLink   │
└────────┬─────────┘
         │
         │ N
         │
         │ 1
┌────────▼─────────┐
│      Claim       │
├──────────────────┤
│ claimId          │
│ claimText        │
│verificationStatus│
└────────┬─────────┘
         │ N
         │
         │ 1
         ▼
┌──────────────────┐
│  DraftRevision   │
├──────────────────┤
│ revisionId       │
│ revisionNumber   │
│ content          │
└─────┬────────┬───┘
      │        │
    N │        │ 1
      ▼        ▼
┌──────────┐ ┌─────────────┐
│  Review  │ │ Publication │
└──────────┘ └─────────────┘
      ▲
      │
      │
   Reviewer


  AssetVersion(old) ─────────┐
                             ▼
                    ┌──────────────────┐
                    │ SourceChangeEvent│◀──── AssetVersion(new)
                    └──────────────────┘
                             │ 1
                             │
                             │ N
                             ▼
                  ┌──────────────────┐
                  │   EvidenceDelta  │──────┐
                  ├──────────────────┤      │ N
                  │ changeClass      │      ▼
                  │ materiality      │ ┌──────────────────┐
                  └────────┬─────────┘ │   ImpactRecord   │
                           │           ├──────────────────┤
                           │ N         │ impactStatus     │
                           ▼           └────────┬─────────┘
                  ┌──────────────────┐           │ N
                  │    ReviewTask    │           ▼
                  ├──────────────────┤   ┌──────────────────┐
                  │ taskType         │   │      Claim       │
                  │ outcome          │   ├──────────────────┤
                  └──────────────────┘   │verificationStatus│
                                        └────────┬─────────┘
                                                 │
                                                 ▼
                                        ┌──────────────────┐
                                        │   Publication    │
                                        └──────────────────┘
```

---

# 20. Critical Domain Relationship

The central architectural concept of the proposed system is:

```text
ASSET
  │
  ▼
ASSET VERSION
  │
  ▼
EVIDENCE PASSAGE
  │
  ▼
EVIDENCE LINK
  │
  ▼
CLAIM
  │
  ▼
DRAFT REVISION
  │
  ▼
REVIEW
  │
  ▼
PUBLICATION
```

The reverse (maintenance) chain runs forward in time when a source changes:

```text
PUBLICATION
  │
  ▼
SOURCE CHANGE EVENT
  │
  ▼
EVIDENCE DELTA
  │
  ▼
IMPACT RECORD
  │
  ▼
REVIEW TASK
  │
  ▼
RE-VERIFIED CLAIM
```

This means that a published claim is not simply stored as generated text.

Its origin remains reconstructable.

Example:

```text
Published Article
        │
        ▼
Revision 4
        │
        ▼
Claim C17
        │
        ▼
Evidence E89
        │
        ▼
42nd Expedition Report — Version 2
        │
        ▼
Page 31
```

This is the foundation of both:

**evidence-backed generation**

and

**source-update impact tracking.**

---

# 21. Source Update Domain Flow

Suppose:

```text
Report A — Version 1
```

supports:

```text
Evidence E1
      │
      ▼
Claim C1
      │
      ▼
Article P1
```

A corrected report is later uploaded:

```text
Report A — Version 2
```

The system performs:

```text
Report A V2 uploaded
        │
        ▼
Hash differs from V1
        │
        ▼
Create new AssetVersion
        │
        ▼
Preserve V1
        │
        ▼
Find evidence belonging to V1
        │
        ▼
Align V1 evidence to V2 evidence  (FR-36)
        │
        ▼
Create EvidenceDelta and classify  (FR-37)
  UNCHANGED / NUMERIC_CHANGED / EVIDENCE_REMOVED / ...
        │
        ▼
Find claims using material deltas  (FR-38)
        │
        ▼
Find published content containing those claims  (FR-39)
        │
        ▼
Create ImpactRecord rows
        │
        ▼
Create ReviewTask per affected publication  (FR-42)
        │
        ▼
Set affected claims to RECHECK_REQUIRED
        │
        ▼
Flag:
SOURCE UPDATED — REVIEW REQUIRED
```

It does **not** automatically claim:

> “The article is wrong.”

Instead it states:

> “A supporting source has changed; review whether the published claim remains valid.”

This is safer and more defensible.

---

# 22. State Model for Outreach Content

## 22.1 Draft and Publication State Model

```text
               ┌─────────┐
               │  DRAFT  │
               └────┬────┘
                    │ submit
                    ▼
              ┌────────────┐
              │ UNDER      │
              │ REVIEW     │
              └─────┬──────┘
                    │
             ┌──────┴───────┐
             │              │
             ▼              ▼
      CHANGES REQUESTED   APPROVED
             │              │
             ▼              ▼
           DRAFT         PUBLISHED
                            │
                            │ source changes
                            ▼
                     REVIEW REQUIRED
                            │
                            ▼
                         REVIEW
```

## 22.2 Claim Verification State Model

```text
                        ┌──────────────┐
        no evidence ───▶│  UNSUPPORTED │◀── evidence removed ──┐
                        └──────┬───────┘                       │
                               │ evidence linked               │
                               ▼                               │
                        ┌──────────────┐                       │
              ┌────────▶│  SUPPORTED   │───────────────────────┤
              │         └──────┬───────┘                       │
              │                │ source changed                │
              │                ▼                               │
              │        ┌───────────────────┐                   │
   human      │        │ RECHECK_REQUIRED  │                   │
   verified   │        └───┬───────────┬───┘                   │
              │            │           │                       │
              │      human says OK   human says revise         │
              │            │           │                       │
              │            │           ▼                       │
              │            │   ┌────────────────┐              │
              │            │   │ NEEDS_REVISION │──────────────┘
              │            │   └───────┬────────┘        revised text
              │            │           │                 has no support
              │            ▼           ▼
              └──────  SUPPORTED   SUPPORTED (after revision
                                       + re-approval)

   permitted sources materially disagree ──▶ ┌──────────┐
                                             │ CONFLICT │
                                             └──────────┘
```

Rules:

- Automated detection may move a claim **into** a review state.
- Only a human `ReviewTask` may move a claim **out of** `RECHECK_REQUIRED`.
- `UNSUPPORTED` and `CONFLICT` claims are not publishable as factual assertions (BR-17).

---

# 23. Main Database-Level Relationships

A possible relational representation is:

```text
USER
 └── USER_ROLE
       └── ROLE

ASSET
 ├── ASSET_VERSION
 │      └── EVIDENCE_PASSAGE
 │
 ├── ASSET_TAG
 ├── EXPEDITION
 └── STATION

DRAFT
 └── DRAFT_REVISION
        ├── CLAIM
        │     └── CLAIM_EVIDENCE
        │             └── EVIDENCE_PASSAGE
        │
        └── REVIEW

PUBLICATION
 └── DRAFT_REVISION

SOURCE_CHANGE_EVENT
 ├── OLD_ASSET_VERSION
 └── NEW_ASSET_VERSION

SOURCE_CHANGE_EVENT
 └── EVIDENCE_DELTA
       ├── OLD_EVIDENCE_PASSAGE
       ├── NEW_EVIDENCE_PASSAGE
       └── IMPACT_RECORD
             ├── CLAIM
             └── PUBLICATION

CLAIM
 └── REVIEW_TASK
       └── (optional) EVIDENCE_DELTA
```

---

# 24. Requirement Traceability Matrix

| Requirement | Use Case | Domain Entity |
|---|---|---|
| FR-03 Asset Upload | UC-01 | Asset |
| FR-04 Metadata | UC-01 | Asset, Metadata |
| FR-06 Processing | UC-01 | AssetVersion |
| FR-10 Keyword Search | UC-02 | EvidencePassage |
| FR-11 Semantic Search | UC-02 | EvidencePassage |
| FR-13 Evidence Retrieval | UC-02 | EvidencePassage |
| FR-15 Content Generation | UC-03 | Draft |
| FR-17 Grounded Generation | UC-03 | Claim, EvidencePassage |
| FR-19 Claim-Evidence Mapping | UC-03 | EvidenceLink |
| FR-20 Draft Versioning | UC-03 | DraftRevision |
| FR-22 Evidence Review | UC-04 | Review |
| FR-24 Revision Approval | UC-04 | Review, DraftRevision |
| FR-26 Publication | UC-05 | Publication |
| FR-29 Source Versioning | UC-06 | AssetVersion |
| FR-31 Change Detection | UC-06 | SourceChangeEvent |
| FR-32 Impact Analysis | UC-06 | Claim, EvidenceLink |
| FR-33 Review Flag | UC-06/07 | Publication |
| FR-36 Evidence Alignment | UC-06 | AssetVersion, EvidencePassage |
| FR-37 Change Classification | UC-06 | EvidenceDelta |
| FR-38 Claim Impact Propagation | UC-06 | Claim, EvidenceLink |
| FR-39 Publication Impact Propagation | UC-06 | DraftRevision, Publication |
| FR-40 Conflict Detection | UC-04/07 | Claim, EvidenceLink |
| FR-41 Insufficient Evidence | UC-03, UC-08 | EvidencePassage |
| FR-42 Re-verification Workflow | UC-07 | ReviewTask, ImpactRecord |
| FR-43 Historical Traceability | UC-05/07 | DraftRevision, AssetVersion |

---

# 25. MVP Scope

To avoid overbuilding, the first working version should demonstrate one complete vertical workflow.

## MVP Must Demonstrate

### Input

One NCPOR PDF.

### Processing

```text
PDF
 ↓
Text extraction
 ↓
Page-aware chunks
 ↓
Embedding/index
```

### Search

```text
Question
 ↓
Relevant passage
 ↓
Original PDF page
```

### Generation

```text
Evidence
 ↓
Generated sentence
 ↓
Claim
 ↓
Evidence ID
```

### Review

```text
Draft + Evidence
 ↓
Reviewer
 ↓
Approve
```

### Update

```text
Modified test PDF
 ↓
Version 2 (V1 preserved)
 ↓
Hash differs → SourceChangeEvent
 ↓
Align V1 evidence to V2 → EvidenceDelta
 ↓
Classify change (e.g. NUMERIC_CHANGED 4.7 → 4.3)
 ↓
Traverse Evidence → Claim → Publication
 ↓
ImpactRecord + ReviewTask
 ↓
Claim: SUPPORTED → RECHECK_REQUIRED
 ↓
"Source Updated — Review Required"
```

That single end-to-end pipeline proves the architecture.

---

# 26. Requirements Prioritization

## MUST HAVE

- Repository
- Upload
- Metadata
- PDF processing
- Keyword search
- Semantic search
- Source-linked search results
- Content generation
- Claim-evidence mapping
- Draft revisions
- Review workflow
- Approval
- Publication
- Basic source versioning
- Source-update detection
- Impact flagging
- Evidence alignment across versions
- Evidence change classification
- Claim verification states
- Re-verification task queue
- Insufficient-evidence abstention
- Historical evidence mapping at approval time

## SHOULD HAVE

- Image management
- Video transcripts
- Dataset previews
- Number/date/unit warnings
- Old-vs-new source comparison
- Audience-specific generation
- Hybrid retrieval/reranking

## COULD HAVE

- Automatic section-level change detection
- Advanced visual analytics
- Direct social-media APIs
- Multilingual content generation
- Personalized recommendations
- Automatic image suggestions
- Advanced analytics dashboard

The **Could Have** features should not delay completion of the core evidence lifecycle.

---

# 27. Acceptance Criteria

The prototype can be considered functionally successful when the team can demonstrate:

### AC-01
An authorized user can upload a PDF.

### AC-02
The PDF becomes searchable.

### AC-03
A query retrieves the relevant passage.

### AC-04
The search result identifies the correct page.

### AC-05
Selecting the result opens the supporting source.

### AC-06
The system generates outreach content using retrieved evidence.

### AC-07
Generated factual claims are associated with real evidence IDs.

### AC-08
Invalid evidence IDs are rejected.

### AC-09
A reviewer can inspect claim and evidence together.

### AC-10
A reviewer can approve or request changes.

### AC-11
Editing approved content creates a new revision requiring review.

### AC-12
An approved revision can become published content.

### AC-13
Uploading a changed version preserves the original version.

### AC-14
The system identifies publications connected to the old version.

### AC-15
Affected publications enter:

**Source Updated — Review Required**

status.

---

### AC-16

Evidence passages from the old version are mapped to their counterparts in the new version, and unmatched passages are reported rather than dropped.

### AC-17

A changed number, date or location in a test report is classified as `NUMERIC_CHANGED`, `DATE_CHANGED` or `LOCATION_CHANGED`.

### AC-18

Every claim dependent on changed evidence is identified, and unrelated claims remain unaffected.

### AC-19

A published claim moves from `SUPPORTED` to `RECHECK_REQUIRED` after a source change, and back to `SUPPORTED` only after a human review task resolves it.

### AC-20

A question absent from the repository returns `INSUFFICIENT_EVIDENCE` with no fabricated citation.

### AC-21

Materially conflicting permitted sources are surfaced to the reviewer rather than silently resolved.

### AC-22

The evidence mapping used at approval time remains reconstructable after later source versions are uploaded.

---

# 28. Validation Requirements

A small labelled evaluation collection should be maintained.

Suggested initial benchmark:

**50 test questions**

including approximately:

**10 questions whose answers are absent from the repository.**

The evaluation should measure:

### Retrieval Quality

Whether a correct supporting passage appears among the top retrieved results.

### Citation Correctness

Whether the linked passage actually supports the generated claim.

### Unsupported Question Handling

Whether the system indicates that sufficient evidence is unavailable rather than fabricating an answer.

### Source Update Detection

Whether content dependent on changed sources is successfully identified.

### False/Over-Flagging

How much unrelated content is unnecessarily sent for review.

### Editorial Effort

Number of factual corrections required per generated draft.

### Time Saved

Comparison of:

**Manual process**

versus

**System-assisted process**

for completing the same outreach task.

### Claim Traceability

Percentage of factual claims that resolve to a valid evidence location **and** exact source version.

### Change Recall

Among deliberately changed evidence units, percentage of dependent claims and publications correctly identified (FR-38/FR-39).

### Evidence Alignment Accuracy

Percentage of old evidence passages correctly matched to their new-version counterparts (FR-36).

### Unsupported-Answer Behaviour

Percentage of unanswerable benchmark questions for which the system returns `INSUFFICIENT_EVIDENCE` instead of fabricating evidence (FR-41).

### Conflict Detection Recall

Percentage of deliberately contradictory source pairs surfaced to the reviewer (FR-40).

---

# 29. Proposed System Architecture

```text
                  ┌─────────────────────────┐
                  │       React + Vite      │
                  │                         │
                  │ Repository              │
                  │ Search                  │
                  │ Outreach Editor         │
                  │ Review Queue            │
                  └────────────┬────────────┘
                               │ REST API
                               ▼
                  ┌─────────────────────────┐
                  │         FastAPI         │
                  │                         │
                  │ Auth / RBAC             │
                  │ Asset API               │
                  │ Search API              │
                  │ Draft Workflow          │
                  │ Review Workflow         │
                  │ Evidence Delta / Impact │
                  └─────────┬───────┬───────┘
                            │       │
              ┌─────────────┘       └─────────────┐
              ▼                                   ▼
     ┌─────────────────┐                 ┌─────────────────┐
     │ PostgreSQL      │                 │ Celery + Redis  │
     │ + pgvector      │                 │ Background Jobs │
     └────────┬────────┘                 └────────┬────────┘
              │                                   │
              │                           ┌───────▼────────┐
              │                           │    Docling     │
              │                           │ Parse/OCR      │
              │                           └───────┬────────┘
              │                                   │
              ▼                                   ▼
     ┌─────────────────────────────────────────────────────┐
     │              Knowledge / Evidence Layer             │
     │                                                     │
     │ Metadata + Chunks + Embeddings + Source Locations  │
     └─────────────────────────┬───────────────────────────┘
                               │
                               ▼
                  ┌────────────────────────┐
                  │ Retrieval + Reranking  │
                  └────────────┬───────────┘
                               │
                               ▼
                  ┌────────────────────────┐
                  │ Configurable LLM       │
                  │ Structured Generation  │
                  └────────────────────────┘
```

---

# 30. Final Domain Summary

The proposed system is not simply:

> **Upload documents → ask AI questions.**

Its domain is:

> **scientific knowledge provenance and outreach lifecycle management.**

The most important entities are:

**Asset**

→ represents a scientific/institutional resource.

**AssetVersion**

→ preserves the exact version of the resource.

**EvidencePassage**

→ represents verifiable information extracted from that exact version.

**Claim**

→ represents a factual statement in outreach content.

**EvidenceLink**

→ records why that claim can be made.

**DraftRevision**

→ preserves editorial history.

**Review**

→ records human scientific/editorial approval.

**Publication**

→ represents approved communication.

**SourceChangeEvent**

→ detects when the evidence underlying previously published content may have changed.

**EvidenceDelta**

→ records which specific passages changed, and how (FR-37).

**ImpactRecord**

→ records which claims and publications are affected by that delta.

**ReviewTask**

→ the human decision point that resolves the impact.

Therefore the system maintains a complete knowledge-provenance chain:

**Source → Version → Evidence → Claim → Draft → Review → Publication → Source Change → Evidence Delta → Impact → Re-review**

This allows the SIH26063 solution to extend beyond conventional repository functionality and address the complete lifecycle of transforming institutional polar-science resources into discoverable, traceable and maintainable public outreach content.