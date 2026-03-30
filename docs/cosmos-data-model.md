# Cosmos DB Data Model — Consent Platform

> **Source:** `consent-data-manager` domain entities + repository query analysis
> **Last updated:** March 2026

## Legend

| Symbol | Meaning                                                                       |
|--------|----------------------------------------------------------------------------|
| ✅      | Field is used in a Cosmos `WHERE` clause / query predicate                    |
| ❌      | Field is **never** used in a Cosmos `WHERE` clause (read-only / display only) |
| 📊     | Field is used in an `ORDER BY` sort clause                                    |
| 🚫     | Field is **never** returned to any API caller                                 |
| 🚫     | Field is **never** returned to any API caller                                 |
| 🔑     | Partition key                                                                 |
| 🆔     | Document `@Id`                                                                |

---

## Architecture Overview

The design uses **one physical container → many logical document types**, discriminated by the `type` field from `AbstractTypedCosmosDocument`.
Container is determined by the entity's abstract parent class (`@Container` annotation), **not** the `type` field.

```
AbstractTypedCosmosDocument
 ├── AbstractCosmosDataSubjectContainer  →  consent-datasubjects
 ├── AbstractCosmosTokenContainer        →  consent-tokens
 └── AbstractCosmosLinkedIdentityGroupContainer → consent-linked-identities

CosmosReceipt               (own @Container) → consent-receipts
CosmosDeletionCertificate   (own @Container) → consent-deletion-certificate
```

---

## Container 1: `consent-datasubjects`

**Autoscale:** 2,000 RU | **TTL:** 155,520,000 sec (~5 years) | **Base:** `AbstractCosmosDataSubjectContainer`

Contains **7 logical document types** in one physical container.

---

### Type: `DataSubject` → `CosmosDataSubject`

**Partition Key:** `identifierHash`

The root data subject document. One document per data subject identifier.

| Field                            | Java Type                     | Queried? | Purpose                                                                             |
|----------------------------------|-------------------------------|----------|-------------------------------------------------------------------------------------|
| `id`                             | `String`                      | 🆔       | Document ID (derived from `identifierHash`)                                         |
| `identifierHash`                 | `String`                      | 🔑 ✅     | SHA hash of DS identifier — PK and equality filter                                  |
| `dataSubjectId`                  | `UUID`                        | ❌        | Internal UUID of the data subject                                                   |
| `identifier`                     | `String`                      | ❌        | Raw identifier (email, user ID, etc.) — encrypted                                   |
| `dataSubjectIdentifierType`      | `String`                      | ✅        | Identifier type filter (`c.dataSubjectIdentifierType = @type`)                      |
| `language`                       | `String`                      | ❌        | Preferred language                                                                  |
| `collectionPointGuid`            | `UUID`                        | ✅        | CP UUID filter (`c.collectionPointGuid = @collectionPointGuid`)                     |
| `collectionPointVersion`         | `Long`                        | ❌        | CP version at creation                                                              |
| `collectionPointType`            | `String`                      | ❌        | CP type                                                                             |
| `confirmationLink`               | `String`                      | ❌        | Double opt-in confirmation URL                                                      |
| `cancellationLink`               | `String`                      | ❌        | Double opt-in cancellation URL                                                      |
| `createdDate`                    | `LocalDateTime`               | ✅ 📊     | Creation date — range filter for deletion scheduler; `ORDER BY c.type, c.createdDate ASC` |
| `lastModifiedDate`               | `LocalDateTime`               | ✅ 📊     | Last modification date — range filter for DS list API; default sort `ORDER BY c.type DESC, c.lastModifiedDate DESC` |
| `lastTransactionDate`            | `LocalDateTime`               | ❌        | Date of last consent transaction                                                    |
| `lastUpdateDateOnDsDocuments`    | `LocalDateTime`               | ❌ 🚫     | Last write date across all DS docs                                                  |
| `testDataSubject`                | `boolean`                     | ✅        | Test flag filter (`c.testDataSubject = @testDataSubject`)                           |
| `doubleOptInEmailOnly`           | `boolean`                     | ❌        | DOI email-only flow flag                                                            |
| `unsubscribe`                    | `boolean`                     | ❌        | Unsubscribe flag                                                                    |
| `futureHardOptOutEnabled`        | `boolean`                     | ❌        | Hard opt-out flag                                                                   |
| `containsLinkTokens`             | `boolean`                     | ✅ 🚫     | Used to find DS missing link tokens: `containsLinkTokens = false OR NOT IS_DEFINED` |
| `inProcess`                      | `boolean`                     | ❌        | Lock flag during active write                                                       |
| `migrated`                       | `boolean`                     | ❌ 🚫     | Migration state flag — indexed but never used as filter                             |
| `lastReceiptGuid`                | `UUID`                        | ❌        | GUID of the last receipt                                                            |
| `endDateOfExclusionFromDeletion` | `LocalDateTime`               | ❌        | Exclusion from deletion expiry                                                      |
| `origin`                         | `Origin`                      | ❌        | Originating source system                                                           |
| `latestGeoLocation`              | `DsGeolocationDto`            | ❌        | Latest known country/state/purposeIds                                               |
| `dataElements`                   | `List<DataElementDto>`        | ✅        | `ARRAY_CONTAINS` on `name` and/or `hashValue`                                       |
| `consentGroups`                  | `List<UUID>`                  | ❌        | Linked identity group IDs                                                           |
| `dsNotices`                      | `List<DsNoticeDto>`           | ❌        | Privacy notices                                                                     |
| `dsAttachments`                  | `List<DsAttachmentDto>`       | ❌        | File attachments                                                                    |
| `purposes`                       | `List<PurposeDto>`            | ✅        | `ARRAY_CONTAINS` on `guid` and `version` for org visibility filter                  |
| `linkTokens`                     | `List<DsEmailLinkTokenDto>`   | ❌        | Active magic link tokens — used as `JOIN` source, not WHERE filter                  |
| `consentStringMetaData`          | `List<ConsentStringMetaData>` | ❌        | Metadata for TCF/GPP consent strings                                                |
| `recentReceipts`                 | `FixedSizeFIFOMap`            | ❌ 🚫     | Inherited — FIFO map of recent receipt IDs                                          |
| `lastProcessedReceiptDate`       | `LocalDateTime`               | ❌ 🚫     | Inherited — date of last processed receipt                                          |
| `type`                           | `String`                      | ✅ 📊     | = `"DataSubject"` — always in WHERE; part of default `ORDER BY c.type` |

---

### Type: `Profile` → `CosmosDataSubjectProfile`

**Partition Key:** `identifierHash`

One document **per data subject × per purpose**. This is the per-purpose consent state record.

| Field                      | Java Type                   | Queried? | Purpose                                                                        |
|----------------------------|-----------------------------|----------|--------------------------------------------------------------------------------|
| `id`                       | `String`                    | 🆔 ✅ 🚫  | Document ID — used as purposeId filter (`c.id = @purposeId`)                   |
| `identifierHash`           | `String`                    | 🔑 ✅ 📊  | Hashed DS identifier — equality filter; `ORDER BY c.identifierHash` in deletion scheduler |
| `purposeId`                | `UUID`                      | ✅        | `ARRAY_CONTAINS` org filter (`c.purposeId, c.purposeVersion`)                  |
| `identifier`               | `String`                    | ❌        | Raw DS identifier                                                              |
| `dataSubjectProfileId`     | `UUID`                      | ❌        | SQL-side DS profile UUID — returned, not filtered                              |
| `purposeName`              | `String`                    | ❌        | Purpose display name                                                           |
| `purposeVersion`           | `Long`                      | ✅        | Used in org-level ARRAY_CONTAINS filter alongside `purposeId`                  |
| `purposeDescription`       | `String`                    | ❌        | Purpose description                                                            |
| `collectionPointId`        | `UUID`                      | ✅        | `c.collectionPointId = @collectionPointId`                                     |
| `collectionPointVersion`   | `Long`                      | ❌        | CP version                                                                     |
| `collectionPointName`      | `String`                    | ❌        | CP name                                                                        |
| `collectionPointType`      | `String`                    | ❌        | CP type                                                                        |
| `totalTransactions`        | `Long`                      | ❌        | Total consent transactions                                                     |
| `lastTransactionId`        | `UUID`                      | ❌        | GUID of last transaction                                                       |
| `status`                   | `String`                    | ✅        | `c.status = @status` (ACTIVE, WITHDRAWN, IMPLICIT, etc.)                       |
| `inProcess`                | `boolean`                   | ❌ 🚫     | Lock flag during write                                                         |
| `consentDate`              | `LocalDateTime`             | ✅        | `c.consentDate < @expiryThreshold` in implicit expiry scheduler                |
| `activationDate`           | `LocalDateTime`             | ❌        | When consent became active                                                     |
| `expiryDate`               | `LocalDateTime`             | ✅        | `c.expiryDate < @expiryThreshold` in explicit expiry scheduler                 |
| `calculatedExpiryDate`     | `LocalDateTime`             | ✅        | `c.calculatedExpiryDate < @expiryThreshold` in calculated expiry scheduler     |
| `removeExpiry`             | `boolean`                   | ✅        | `c.removeExpiry = false OR NOT IS_DEFINED(c.removeExpiry)` in expiry scheduler |
| `firstTransactionDate`     | `LocalDateTime`             | ❌        | Date of first transaction                                                      |
| `lastTransactionDate`      | `LocalDateTime`             | ✅        | `c.lastTransactionDate < @expiryThreshold` in implicit expiry scheduler        |
| `lastUpdatedDate`          | `LocalDateTime`             | ✅ 📊     | `c.lastUpdatedDate >= @updatedSince` / `<= @updatedUntil`; default sort `ORDER BY c.type DESC, c.lastUpdatedDate DESC` |
| `lastInteractionDate`      | `LocalDateTime`             | ✅        | `c.lastInteractionDate >= @from AND <= @to` for deletion scheduler             |
| `withdrawalDate`           | `LocalDateTime`             | ❌        | Withdrawal date                                                                |
| `withdrawnBy`              | `String`                    | ❌        | Who withdrew                                                                   |
| `withdrawalNotes`          | `String`                    | ❌        | Notes on withdrawal                                                            |
| `doubleOptInConsent`       | `boolean`                   | ❌        | DOI consent flag                                                               |
| `receiptGuid`              | `UUID`                      | ❌        | Associated receipt GUID                                                        |
| `receiptDate`              | `Instant`                   | ❌        | Associated receipt date                                                        |
| `orgGroupId`               | `UUID`                      | ❌        | Organization group UUID                                                        |
| `migrated`                 | `boolean`                   | ❌ 🚫     | Migration flag                                                                 |
| `purposeType`              | `String`                    | ❌ 🚫     | Type of purpose                                                                |
| `topicsList`               | `List<UUID>`                | ❌        | Topics opted in                                                                |
| `topicsNotConsentedTo`     | `List<UUID>`                | ❌        | Topics NOT opted in                                                            |
| `customPreferencesMap`     | `Map<UUID, List<UUID>>`     | ❌        | Custom preference → selected options                                           |
| `purposeOrganizationIds`   | `List<String>`              | ❌        | Org IDs for purpose                                                            |
| `attributes`               | `Map<String, List<String>>` | ❌        | Extra purpose-level attributes                                                 |
| `dsAttachments`            | `List<DsAttachmentDto>`     | ❌        | Purpose-level attachments                                                      |
| `purposeNote`              | `DsPurposeNoteDto`          | ❌        | Unsubscribe/note detail                                                        |
| `geolocation`              | `DsGeolocationDto`          | ❌        | Geolocation at consent time                                                    |
| `firstReceiptInfo`         | `FirstReceiptInfo`          | ❌        | First receipt details                                                          |
| `latestActiveReceiptInfo`  | `ReceiptInfo`               | ❌        | Latest active receipt details                                                  |
| `latestReceiptInfo`        | `ReceiptInfo`               | ❌        | Latest receipt details                                                         |
| `purposeScopes`            | `List<DsPurposeScope>`      | ✅        | `ARRAY_CONTAINS` on `key` + `value` pairs                                      |
| `recentReceipts`           | `FixedSizeFIFOMap`          | ❌ 🚫     | Inherited                                                                      |
| `lastProcessedReceiptDate` | `LocalDateTime`             | ❌ 🚫     | Inherited                                                                      |
| `type`                     | `String`                    | ✅ 📊 🚫  | = `"Profile"` — always in WHERE; part of default `ORDER BY c.type DESC` |

---

### Type: `ConsentString` → `CosmosDataSubjectConsentString`

**Partition Key:** `identifierHash`

Stores TCF/GPP consent strings for a data subject.

| Field                                    | Java Type          | Queried? | Purpose                                     |
|------------------------------------------|--------------------|----------|---------------------------------------------|
| `id`                                     | `String`           | 🆔 ❌ 🚫  | Document ID                                 |
| `identifierHash`                         | `String`           | 🔑 ✅ 🚫  | Hashed DS identifier                        |
| `cosmosConsentStrings[].type`            | `String`           | ❌        | String type (`GPP`, `TCF_EU`, `TCF_CANADA`) |
| `cosmosConsentStrings[].content`         | `String`           | ❌        | Raw encoded consent string                  |
| `cosmosConsentStrings[].receivedDate`    | `LocalDateTime`    | ❌        | When the string was received                |
| `cosmosConsentStrings[].interactionDate` | `LocalDateTime`    | ❌        | DS interaction date                         |
| `recentReceipts`                         | `FixedSizeFIFOMap` | ❌ 🚫     | Inherited                                   |
| `lastProcessedReceiptDate`               | `LocalDateTime`    | ❌ 🚫     | Inherited                                   |
| `type`                                   | `String`           | ✅ 🚫     | = `"ConsentString"` — always in WHERE       |

---

### Type: `DataSubjectDeletionExcluded` → `CosmosDataSubjectDeletionExclusion`

**Partition Key:** `identifierHash`

Guards a data subject from deletion workflows for a defined period.

| Field                | Java Type       | Queried? | Purpose                                             |
|----------------------|-----------------|----------|-----------------------------------------------------|
| `id`                 | `String`        | 🆔 ❌ 🚫  | Document ID                                         |
| `identifierHash`     | `String`        | 🔑 ✅ 🚫  | Hashed DS identifier                                |
| `endDateOfExclusion` | `LocalDateTime` | ❌        | Date the exclusion expires                          |
| `ttl`                | `Long`          | ❌ 🚫     | Cosmos document-level TTL override                  |
| `type`               | `String`        | ✅ 🚫     | = `"DataSubjectDeletionExcluded"` — always in WHERE |

---

### Type: `LinkedIdentityGroup` → `CosmosLinkedIdentityGroup`

**Partition Key:** `identifierHash`

DS-centric LIG view. One document per DS membership. Lives in `consent-datasubjects` for deletion and resolution workflows.

| Field                   | Java Type       | Queried? | Purpose                                                    |
|-------------------------|-----------------|----------|------------------------------------------------------------|
| `linkedIdentityGroupId` | `String`        | 🆔 ✅     | @Id and IN clause filter (`c.linkedIdentityGroupId in @p`) |
| `identifierHash`        | `String`        | 🔑 ✅ 🚫  | Equality and IN clause filter                              |
| `name`                  | `String`        | ❌        | Group name                                                 |
| `identifier`            | `String`        | ❌        | Raw DS identifier                                          |
| `identifierType`        | `String`        | ❌ 🚫     | Identifier type                                            |
| `primary`               | `boolean`       | ✅        | `c.primary = @primary` — find primary members              |
| `addedDate`             | `LocalDateTime` | ❌        | When DS was added to group                                 |
| `updatedDate`           | `LocalDateTime` | ❌ 🚫     | Last update date                                           |
| `purposeOrganisation`   | `List<String>`  | ❌ 🚫     | Orgs associated with this group member                     |
| `dataSubjectGuid`       | `UUID`          | ❌ 🚫     | DS internal UUID                                           |
| `type`                  | `String`        | ✅ 🚫     | = `"LinkedIdentityGroup"` — always in WHERE                |

---

### Type: `DataSubjectIdDictionary` → `CosmosDataSubjectIdDictionary`

**Partition Key:** `identifierHash`

Maps a DS GUID hash → DS identifier hash. Enables lookup by DS GUID.

| Field              | Java Type | Queried?   | Purpose                                                             |
|--------------------|-----------|------------|---------------------------------------------------------------------|
| `identifierHash`   | `String`  | 🔑 🆔 ✅ 🚫 | Hash of DS GUID — PK and equality / IN filter                       |
| `dsIdentifierHash` | `String`  | ✅ 🚫       | `c.dsIdentifierHash = @identifierHash` for reverse mapping deletion |
| `type`             | `String`  | ✅ 🚫       | = `"DataSubjectIdDictionary"` — always in WHERE                     |

---

### Type: `AdditionalIdDictionary` → `CosmosAdditionalIdDictionary`

**Partition Key:** `identifierHash`

Maps an additional identifier hash → primary identifier hash.

| Field                   | Java Type | Queried? | Purpose                                                               |
|-------------------------|-----------|----------|-----------------------------------------------------------------------|
| `identifierHash`        | `String`  | 🔑 🆔 ✅ 🚫 | Hash of additional identifier — PK and equality filter                |
| `primaryIdentifierHash` | `String`  | ❌ 🚫     | Hash of the primary identifier — returned from lookup, never filtered |
| `type`                  | `String`  | ✅ 🚫     | = `"AdditionalIdDictionary"` — always in WHERE                        |

---

## Container 2: `consent-tokens`

**Autoscale:** 1,000 RU | **TTL:** 155,520,000 sec (~5 years) | **Base:** `AbstractCosmosTokenContainer`

---

### Type: `DataSubjectAccessToken` → `CosmosDataSubjectAccessToken`

**Partition Key:** `token`

Stores DOI and notification access tokens. Used for email verification and re-confirmation flows.

| Field | Java Type | Queried? | Purpose |
|---|---|---|---|
| `token` | `String` | 🔑 🆔 ❌ | PK — used in `findById` / `deleteById` only |
| `identifierHash` | `String` | ✅ | `c.identifierHash = @identifierHash` — find tokens by DS |
| `tokenType` | `String` | ✅ | `c.tokenType = 'NOTIFICATION_TOKEN'` in notification lookup |
| `tokenOrigin` | `String` | ❌ | Source that generated the token |
| `retryCount` | `String` | ✅ | `c.retryCount < @retryCount` or `>= @retryCount` in DOI scheduler |
| `collectionPointId` | `UUID` | ✅ | `c.collectionPointId IN (...)` in DOI scheduler |
| `collectionPointVersion` | `Long` | ❌ | CP version |
| `receiptGuid` | `UUID` | ❌ 🚫 | Associated receipt GUID |
| `purposes` | `List<DsAccessTokenPurpose>` | ✅ | `ARRAY_CONTAINS(c.purposes, {guid: @purposeId}, true)` |
| `recordDate` | `LocalDateTime` | ✅ 🚫 | `c.recordDate < @recordDateTime` in DOI scheduler (when migrated) |
| `_ts` | `long` | ✅ 🚫 | `c._ts < @timestamp` in DOI scheduler (legacy pre-migration) |
| `type` | `String` | ✅ 🚫 | = `"DataSubjectAccessToken"` — always in WHERE |

---

### Type: `LinkTokenDictionary` → `CosmosLinkTokenDictionary`

**Partition Key:** `token`

Maps a magic link token → DS identifier for preference-center login flows.

| Field            | Java Type       | Queried? | Purpose                                                                                                   |
|------------------|-----------------|----------|-----------------------------------------------------------------------------------------------------------|
| `tokenHash`      | `String`        | 🆔 ❌     | @Id — hash of the token, not used as WHERE filter                                                         |
| `token`          | `String`        | 🔑 ❌     | PK — used in `findById` / `deleteById` only                                                               |
| `identifierHash` | `String`        | ✅        | `c.identifierHash = @identifierHash` — find tokens by DS for deletion                                     |
| `identifier`     | `String`        | ❌        | Raw DS identifier                                                                                         |
| `recordDate`     | `LocalDateTime` | ✅        | `c.recordDate >= @fromDate / <= @toDate` (when migrated)                                                  |
| `expiryDate`     | `LocalDateTime` | ✅        | `c.expiryDate < @expiryDate`, `NOT IS_NULL(c.expiryDate)`                                                 |
| `_ts`            | `long`          | ✅ 📊 🚫  | `c._ts >= @fromDate / <= @toDate` (legacy pre-migration); `ORDER BY c.type ASC, c._ts ASC` (default sort) |
| `type`           | `String`        | ✅ 📊 🚫  | = `"LinkTokenDictionary"` — always in WHERE; part of default `ORDER BY c.type ASC`                        |

---

## Container 3: `consent-linked-identities`

**Autoscale:** 1,000 RU | **TTL:** 155,520,000 sec (~5 years) | **Base:** `AbstractCosmosLinkedIdentityGroupContainer`

Group-centric LIG model (V2). One document per group.

---

### Type: `LinkedIdentityGroup` → `CosmosLinkedIdentityGroupV2`

**Partition Key:** `linkedIdentityPartitionKey`

| Field                        | Java Type                                 | Queried? | Purpose                                                                                            |
|------------------------------|-------------------------------------------|----------|----------------------------------------------------------------------------------------------------|
| `linkedIdentityPartitionKey` | `String`                                  | 🔑 🆔 ❌  | PK — used in `findById` / `deleteById` only                                                        |
| `linkedIdentityGroupId`      | `String`                                  | ❌ 🚫     | LIG UUID — stored separately for reference, not filtered                                           |
| `name`                       | `String`                                  | ✅        | `c.name = @groupName` — find group by name                                                         |
| `identifierTypes`            | `List<String>`                            | ✅        | `ARRAY_CONTAINS(c.identifierTypes, @identifierType, true)`                                         |
| `primary`                    | `List<LinkedIdentityGroupDataSubjectDto>` | ✅        | `ARRAY_CONTAINS(c.primary, {identifierHash, identifierType}, true)`                                |
| `members`                    | `List<LinkedIdentityGroupDataSubjectDto>` | ✅        | `ARRAY_CONTAINS(c.members, {identifierHash, identifierType}, true)`                                |
| `addedDate`                  | `LocalDateTime`                           | ❌ 📊     | Group creation date — `ORDER BY c.type DESC, c.addedDate DESC` (default sort); never used in WHERE |
| `updatedDate`                | `LocalDateTime`                           | ❌        | Last update                                                                                        |
| `type`                       | `String`                                  | ✅ 📊 🚫  | = `"LinkedIdentityGroup"` — always in WHERE; part of default `ORDER BY c.type DESC`                |

---

### Type: `LinkedIdentityGroupDictionary` → `CosmosLinkedIdentityGroupDictionary`

**Partition Key:** `linkedIdentityPartitionKey`

Per-DS lookup: which LIGs does this DS belong to?

| Field                        | Java Type    | Queried?   | Purpose                                                      |
|------------------------------|--------------|------------|--------------------------------------------------------------|
| `linkedIdentityPartitionKey` | `String`     | 🔑 🆔 ✅ 🚫 | PK — used in `findById` (DS identifier hash)                 |
| `primaryLinkedGroups`        | `List<UUID>` | ❌ 🚫       | LIG IDs where DS is primary — read after fetch, not filtered |
| `memberLinkedGroups`         | `List<UUID>` | ❌ 🚫       | LIG IDs where DS is member — read after fetch, not filtered  |
| `type`                       | `String`     | ✅ 🚫       | = `"LinkedIdentityGroupDictionary"` — always in WHERE        |

---

## Container 4: `consent-deletion-certificate`

**Autoscale:** 1,000 RU | **TTL:** 7,776,000 sec (90 days) | **Direct `@Container` on entity**

Single-type container. Audit trail for GDPR deletions.

---

### Type: `DeletionCertificate` → `CosmosDeletionCertificate`

**Partition Key:** `identifierHash`

| Field            | Java Type                   | Queried? | Purpose                                                         |
|------------------|-----------------------------|----------|-----------------------------------------------------------------|
| `id`             | `String`                    | 🆔 ❌ 🚫  | Document ID                                                     |
| `identifierHash` | `String`                    | 🔑 ✅ 🚫  | Optional equality filter (`c.identifierHash = @identifierHash`) |
| `objectId`       | `UUID`                      | ❌        | ID of the deleted object                                        |
| `objectType`     | `DeleteObjectType`          | ❌        | What was deleted (DS, PROFILE, etc.)                            |
| `deleteTime`     | `LocalDateTime`             | ❌        | When the deletion occurred                                      |
| `deleteType`     | `DeleteType`                | ❌        | Type of deletion (GDPR, SCHEDULED, etc.)                        |
| `deletedIn`      | `List<DeleteSourceDetails>` | ❌ 🚫     | Storage targets deleted (container + timestamp)                 |
| `type`           | `String`                    | ✅ 🚫     | = `"DeletionCertificate"` — always in WHERE                     |

---

## Container 5: `consent-receipts`

**Autoscale:** 1,000 RU | **TTL:** 7,776,000 sec (90 days) | **Direct `@Container` on entity**

Primary receipt store. Receipts older than 90 days fall through to SQL archive.

---

### Type: (no discriminator) → `CosmosReceipt`

**Partition Key:** `identifierHash`

| Field                    | Java Type                    | Queried? | Purpose                                                                                                |
|--------------------------|------------------------------|----------|--------------------------------------------------------------------------------------------------------|
| `id`                     | `String`                     | 🆔 ✅ 📊  | Receipt document ID — `c.id = @receiptGuid`; `ORDER BY r.id ASC` in deletion batch query               |
| `identifierHash`         | `String`                     | 🔑 ✅     | PK and equality filter (`c.identifierHash = @hash`)                                                    |
| `identifier`             | `String`                     | ❌        | Raw DS identifier — encrypted                                                                          |
| `otJwtVersion`           | `Long`                       | ❌        | JWT version of the CP token                                                                            |
| `customPayload`          | `String`                     | ❌ 🚫     | Custom key-value payload — not present in `CosmosReceiptDocument` query model                          |
| `collectionPointUUID`    | `UUID`                       | ✅        | `c.collectionPointUUID = @collectionPointGuid`                                                         |
| `collectionPointVersion` | `Long`                       | ❌        | CP version                                                                                             |
| `collectionPointType`    | `String`                     | ✅        | `c.collectionPointType = 'ADMIN_UPDATE'` in org visibility filter                                      |
| `consentCreationDate`    | `LocalDateTime`              | ✅ 📊     | `>= @fromDate`, `<= @toDate`, `< @cutOffTime`; always sorted `ORDER BY r.consentCreationDate ASC/DESC` |
| `interactionDate`        | `LocalDateTime`              | ❌        | DS interaction timestamp — indexed but never WHERE-filtered                                            |
| `test`                   | `Boolean`                    | ❌        | Test receipt flag                                                                                      |
| `origin`                 | `Origin`                     | ❌        | Originating system                                                                                     |
| `doubleOptIn`            | `Boolean`                    | ❌        | DOI flag                                                                                               |
| `language`               | `Locale`                     | ❌        | DS language at consent time                                                                            |
| `isAnonymous`            | `Boolean`                    | ❌        | Anonymous consent flag — passed as API param but not used in Cosmos WHERE                              |
| `organizationId`         | `UUID`                       | ✅        | `c.organizationId IN (@orgIds)` for org visibility filter                                              |
| `unsubscribe`            | `boolean`                    | ❌        | Unsubscribe flag                                                                                       |
| `dataElements`           | `Map<String, Object>`        | ✅        | `c.dataElements['key']['valueHash'] = @value`                                                          |
| `additionalIdentifiers`  | `Map<String, Object>`        | ❌        | Additional identifiers — indexed but never WHERE-filtered                                              |
| `attributes`             | `Map<String, List<Object>>`  | ❌        | Arbitrary attributes                                                                                   |
| `ruleEvaluationResults`  | `List<RuleEvaluationResult>` | ❌        | Rule engine outcomes                                                                                   |
| `attachments`            | `List<CosmosAttachments>`    | ❌        | File attachment IDs                                                                                    |
| `consentString`          | `ConsentString`              | ❌        | TCF/GPP consent string                                                                                 |
| `source`                 | `Source`                     | ❌        | Source info                                                                                            |
| `geolocation`            | `CosmosGeolocation`          | ❌        | country, state, stateName, purposeIds                                                                  |
| `ts`                     | `long`                       | ❌ 🚫     | Cosmos system timestamp (`_ts`)                                                                        |
| `purposes`               | `List<CosmosPurpose>`        | ❌        | Per-purpose consent details — returned, not WHERE-filtered in Cosmos                                   |

**`CosmosPurpose` (nested in `purposes[]`):** All nested fields are ❌ — `purposes[]` is **not** filtered in Cosmos WHERE clauses for the receipts container. Purpose-level filtering (if needed) is done in-memory or via SQL in the archived receipts path.

| Nested Field | Java Type | Queried? |
|---|---|---|
| `guid` / `purposeGuid` | `UUID` | ❌ |
| `transactionGuid` | `UUID` | ❌ |
| `purposeVersion` | `Long` | ❌ |
| `transactionType` | `TransactionType` | ❌ |
| `consentDate` | `LocalDateTime` | ❌ |
| `issueDate` | `LocalDateTime` | ❌ |
| `withdrawalDate` | `LocalDateTime` | ❌ |
| `activationDate` | `LocalDateTime` | ❌ |
| `expiryDate` | `LocalDateTime` | ❌ |
| `removeExpiry` | `boolean` | ❌ |
| `topics` | `List<CosmosPreference>` | ❌ |
| `customPreferences` | `List<CosmosCustomPreferences>` | ❌ |
| `purposeAttachments` | `List<CosmosAttachments>` | ❌ |
| `purposeNote` | `CosmosPurposeNote` | ❌ |
| `purposePrivacyNotices` | `List<CosmosPrivacyNotice>` | ❌ |
| `collectionPointPrivacyNotices` | `List<CosmosPrivacyNotice>` | ❌ |
| `attributes` | `Map<String, List<String>>` | ❌ |
| `purposeScopes` | `List<DsPurposeScope>` | ❌ |

---

## Summary Reference Table

| Container | Document Type | Java Entity | Partition Key | TTL | WHERE / ORDER BY Fields (📊 = sort-only) |
|---|---|---|---|---|
| `consent-datasubjects` | `DataSubject` | `CosmosDataSubject` | `identifierHash` | ~5 yr | `type` ✅📊, `identifierHash`, `lastModifiedDate` ✅📊, `createdDate` ✅📊, `testDataSubject`, `dataSubjectIdentifierType`, `collectionPointGuid`, `containsLinkTokens`, `dataElements[].name/hashValue`, `purposes[].guid/version` |
| `consent-datasubjects` | `Profile` | `CosmosDataSubjectProfile` | `identifierHash` | ~5 yr | `type` ✅📊, `identifierHash` ✅📊, `id` (purposeId), `purposeId`, `purposeVersion`, `collectionPointId`, `status`, `lastUpdatedDate` ✅📊, `lastInteractionDate`, `expiryDate`, `calculatedExpiryDate`, `removeExpiry`, `consentDate`, `lastTransactionDate`, `purposeScopes[].key/value` |
| `consent-datasubjects` | `ConsentString` | `CosmosDataSubjectConsentString` | `identifierHash` | ~5 yr | `type`, `identifierHash` |
| `consent-datasubjects` | `DataSubjectDeletionExcluded` | `CosmosDataSubjectDeletionExclusion` | `identifierHash` | ~5 yr | `type`, `identifierHash` |
| `consent-datasubjects` | `LinkedIdentityGroup` | `CosmosLinkedIdentityGroup` | `identifierHash` | ~5 yr | `type`, `identifierHash`, `linkedIdentityGroupId`, `primary` |
| `consent-datasubjects` | `DataSubjectIdDictionary` | `CosmosDataSubjectIdDictionary` | `identifierHash` | ~5 yr | `type`, `identifierHash`, `dsIdentifierHash` |
| `consent-datasubjects` | `AdditionalIdDictionary` | `CosmosAdditionalIdDictionary` | `identifierHash` | ~5 yr | `type`, `identifierHash` |
| `consent-tokens` | `DataSubjectAccessToken` | `CosmosDataSubjectAccessToken` | `token` | ~5 yr | `type`, `identifierHash`, `tokenType`, `retryCount`, `collectionPointId`, `purposes[].guid`, `recordDate`, `_ts` |
| `consent-tokens` | `LinkTokenDictionary` | `CosmosLinkTokenDictionary` | `token` | ~5 yr | `type` ✅📊, `identifierHash`, `expiryDate`, `recordDate`, `_ts` ✅📊 |
| `consent-linked-identities` | `LinkedIdentityGroup` | `CosmosLinkedIdentityGroupV2` | `linkedIdentityPartitionKey` | ~5 yr | `type` ✅📊, `name`, `identifierTypes`, `primary[].identifierHash/identifierType`, `members[].identifierHash/identifierType`, `addedDate` ❌📊 |
| `consent-linked-identities` | `LinkedIdentityGroupDictionary` | `CosmosLinkedIdentityGroupDictionary` | `linkedIdentityPartitionKey` | ~5 yr | `type`, `linkedIdentityPartitionKey` (findById) |
| `consent-receipts` | *(none)* | `CosmosReceipt` | `identifierHash` | 90 days | `id` ✅📊, `identifierHash`, `collectionPointUUID`, `collectionPointType`, `consentCreationDate` ✅📊, `organizationId`, `dataElements[key].valueHash` |
| `consent-deletion-certificate` | `DeletionCertificate` | `CosmosDeletionCertificate` | `identifierHash` | 90 days | `type`, `identifierHash` |

---

## Key Observations

1. **Receipts container is read-heavy on very few fields** — of all the fields stored in `CosmosReceipt`, only 7 fields are ever queried; all `purposes[]` sub-fields (20+ fields) are never WHERE-filtered in Cosmos.

2. **`consent-datasubjects` carries the highest query complexity** — 14 distinct fields are WHERE-filtered across its 7 document types, with composite indexes defined on `consent-datasubjects` to support them.

3. **`ConsentString` and `DeletionExcluded` types are lookup-only** — they are always fetched by `identifierHash` (PK) + `type`, and none of their payload fields are ever used as filters.

4. **`LinkedIdentityGroupDictionary` fields are never queried** — `primaryLinkedGroups` and `memberLinkedGroups` are always read after a `findById(PK)` lookup, never used as WHERE filters.

5. **`isAnonymous` on receipts is never used as a Cosmos WHERE filter** — despite being indexed and passed as an API parameter, filtering is not pushed down to Cosmos.

6. **`interactionDate` on receipts is indexed but never WHERE-filtered** — it is only used in the application layer for expiry calculations.

7. **`additionalIdentifiers` on receipts is indexed but never WHERE-filtered**.

8. **Legacy `_ts` field** in `consent-tokens` — both `DataSubjectAccessToken` and `LinkTokenDictionary` fall back to `_ts`-based filtering when `recordDate` migration has not been completed.

---

## Fields Never Returned to Any API Caller (🚫)

| Container                      | Document Type                   | Field                         | Notes                                                                |
|--------------------------------|---------------------------------|-------------------------------|----------------------------------------------------------------------|
| `consent-datasubjects`         | `DataSubject`                   | `containsLinkTokens`          | Scheduler-only write flag; never in any response DTO                 |
| `consent-datasubjects`         | `DataSubject`                   | `migrated`                    | Migration-era artefact; no live read path                            |
| `consent-datasubjects`         | `DataSubject`                   | `lastUpdateDateOnDsDocuments` | Internal write-tracking field                                        |
| `consent-datasubjects`         | `DataSubject`                   | `recentReceipts`              | Inherited base field; absent from all response DTOs                  |
| `consent-datasubjects`         | `DataSubject`                   | `lastProcessedReceiptDate`    | Inherited base field; absent from all response DTOs                  |
| `consent-datasubjects`         | `Profile`                       | `id`                          | `@JsonIgnore` in `DsProfileDto` — never serialised                   |
| `consent-datasubjects`         | `Profile`                       | `type`                        | Discriminator; absent from `DsProfileDto` and integration DTO        |
| `consent-datasubjects`         | `Profile`                       | `inProcess`                   | Lock flag; exposed on DS document but hidden on Profile              |
| `consent-datasubjects`         | `Profile`                       | `migrated`                    | Migration flag; same as DS                                           |
| `consent-datasubjects`         | `Profile`                       | `purposeType`                 | Set on write; absent from all profile response DTOs                  |
| `consent-datasubjects`         | `Profile`                       | `recentReceipts`              | Inherited base field                                                 |
| `consent-datasubjects`         | `Profile`                       | `lastProcessedReceiptDate`    | Inherited base field                                                 |
| `consent-datasubjects`         | `ConsentString`                 | `id`                          | Document ID; infrastructure-only                                     |
| `consent-datasubjects`         | `ConsentString`                 | `identifierHash`              | Hashed PK; never surfaced to callers                                 |
| `consent-datasubjects`         | `ConsentString`                 | `type`                        | Discriminator                                                        |
| `consent-datasubjects`         | `ConsentString`                 | `recentReceipts`              | Inherited base field                                                 |
| `consent-datasubjects`         | `ConsentString`                 | `lastProcessedReceiptDate`    | Inherited base field                                                 |
| `consent-datasubjects`         | `DataSubjectDeletionExcluded`   | `id`                          | Document ID                                                          |
| `consent-datasubjects`         | `DataSubjectDeletionExcluded`   | `identifierHash`              | Hashed PK                                                            |
| `consent-datasubjects`         | `DataSubjectDeletionExcluded`   | `ttl`                         | Cosmos TTL override; internal                                        |
| `consent-datasubjects`         | `DataSubjectDeletionExcluded`   | `type`                        | Discriminator                                                        |
| `consent-datasubjects`         | `LinkedIdentityGroup` (V1)      | `identifierHash`              | Hashed PK                                                            |
| `consent-datasubjects`         | `LinkedIdentityGroup` (V1)      | `identifierType`              | Not in `LinkedIdentityGroupDto`                                      |
| `consent-datasubjects`         | `LinkedIdentityGroup` (V1)      | `updatedDate`                 | Not in `LinkedIdentityGroupDto`                                      |
| `consent-datasubjects`         | `LinkedIdentityGroup` (V1)      | `purposeOrganisation`         | Not in any response DTO                                              |
| `consent-datasubjects`         | `LinkedIdentityGroup` (V1)      | `dataSubjectGuid`             | Not in any response DTO                                              |
| `consent-datasubjects`         | `LinkedIdentityGroup` (V1)      | `type`                        | Discriminator                                                        |
| `consent-datasubjects`         | `DataSubjectIdDictionary`       | *(all fields)*                | Pure internal lookup; no endpoint exposes this document              |
| `consent-datasubjects`         | `AdditionalIdDictionary`        | *(all fields)*                | Pure internal lookup; no endpoint exposes this document              |
| `consent-tokens`               | `DataSubjectAccessToken`        | `receiptGuid`                 | Not in `DataSubjectAccessTokenDto`                                   |
| `consent-tokens`               | `DataSubjectAccessToken`        | `recordDate`                  | Queried by scheduler; not in `DataSubjectAccessTokenDto`             |
| `consent-tokens`               | `DataSubjectAccessToken`        | `_ts`                         | Legacy scheduler field; never in response                            |
| `consent-tokens`               | `DataSubjectAccessToken`        | `type`                        | Discriminator                                                        |
| `consent-tokens`               | `LinkTokenDictionary`           | `_ts`                         | Legacy scheduler field                                               |
| `consent-tokens`               | `LinkTokenDictionary`           | `type`                        | Discriminator                                                        |
| `consent-linked-identities`    | `LinkedIdentityGroupV2`         | `linkedIdentityGroupId`       | Not in `CosmosLinkedIdentityGroupResponseDto`; PK alias used instead |
| `consent-linked-identities`    | `LinkedIdentityGroupV2`         | `type`                        | Discriminator                                                        |
| `consent-linked-identities`    | `LinkedIdentityGroupDictionary` | *(all fields)*                | Pure internal lookup; no endpoint exposes this document              |
| `consent-deletion-certificate` | `DeletionCertificate`           | `id`                          | Document ID; infrastructure-only                                     |
| `consent-deletion-certificate` | `DeletionCertificate`           | `identifierHash`              | Hashed PK                                                            |
| `consent-deletion-certificate` | `DeletionCertificate`           | `deletedIn`                   | Selected in query but absent from `DeletionCertificationResponse`    |
| `consent-deletion-certificate` | `DeletionCertificate`           | `type`                        | Discriminator                                                        |
| `consent-receipts`             | `CosmosReceipt`                 | `customPayload`               | Not declared in `CosmosReceiptDocument`; never in receipt responses  |
| `consent-receipts`             | `CosmosReceipt`                 | `ts`                          | Cosmos system `_ts`; never serialised                                |
