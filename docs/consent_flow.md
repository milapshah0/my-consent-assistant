# Complete Consent Flow

## Receipt Creation via DS-Request
- First step is creating receipt which records the consent given by the user for various purposes from a given collection point.
- Reference: https://developer.onetrust.com/onetrust/reference/createconsentreceiptusingpost
    - POST: https://{hostname}/request/v1/consentreceipts
      > |
        ```text
        Each collection point must first be set up in the OneTrust Platform to generate a valid JWT, which must be present in the request payload. The JWT can be found on the Integrations tab of the Collection point details screen within the platform or can be retrieved by calling the Get Collection Point Token API.
        Once the test parameter is set to true, reverting it to false is not possible. However, transitioning from test=false to test=true is supported. For more information on how to remove the test flag in the OneTrust Platform, see Managing Data Subject Records.
        In most cases, further authorization is not required. However, additional information for setting up authenticated consent can be found here when needed.
        Please avoid passing privacy notices for regular Custom API collection points. OneTrust strongly recommends using privacyNotices only for those enabled with dynamic configuration, as they allow you to gather information about all purposes.
        When passing the purposes parameter, the version for PrivacyNotices will be used based on the consent date.
        OneTrust recommends including no more than 10 purposes per consent receipt, with an absolute maximum of 20 purposes.
        Please validate all inputs before sending data to a Custom API collection point. This API does not perform data type validation to ensure high performance and fast response times. However, invalid data will not be passed to the data subject.
        ```
        - Request Body

          **Minimal example**
          ```json
          {
            "requestInformation": "<collection-point-jwt>",
            "identifier": "user@example.com",
            "identifierType": "EMAIL",
            "purposes": [
              {
                "Id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "Version": 1,
                "TransactionType": "CONFIRMED"
              }
            ]
          }
          ```

          **Top-level fields**

          | Field | Type | Required | Description |
          |---|---|:---:|---|
          | `requestInformation` | string | ✅ | JWT for the collection point. |
          | `identifier` | string | ✅ | Data subject identifier (max 700 chars). |
          | `identifierType` | string | | Type of identifier used as the primary identifier. |
          | `test` | boolean | | Mark receipt as a test (default `false`). Once set to `true`, cannot be reverted to `false` via API. |
          | `generateInstantLinkToken` | boolean | | Generate a DS link token (JWT, expires 12 months). API-type CPs only. Mutually exclusive with `shortLinkToken`. |
          | `shortLinkToken` | boolean | | Generate a shortened DS link token. API-type CPs only. Mutually exclusive with `generateInstantLinkToken`. |
          | `language` | string | | ISO language code (e.g. `en-US`). |
          | `interactionDate` | string | | ISO 8601 date-time of the consent interaction. |
          | `enableDataElementDateValidation` | boolean | | If `true`, DS data element values are overwritten only when the receipt interaction date is later than the last updated date of the data subject. |
          | `consentString` | object | | GPP / TCF consent string. See [`consentString`](#consentstring). |
          | `receiptOptions` | array | | Receipt processing options. See [`receiptOptions[]`](#receiptoptions). |
          | `source` | object | | Source where the consent interaction occurred. See [`source`](#source). |
          | `parentPrimaryIdentifiers` | array | | Parent DS identifiers for LIG linking. Requires **Enable Parent-child relationship** on the CP. See [`parentPrimaryIdentifiers[]`](#parentprimaryidentifiers). |
          | `dsDataElements` | object | | Additional DS info as key-value pairs (total max 4,000 chars; per-value max 750 chars; max 25 items for multi-select). |
          | `customPayload` | object | | Custom key-value pairs stored on the receipt (max 4,000 chars total). |
          | `additionalIdentifiers` | object | | Secondary identifiers (e.g. secondary email) as key-value pairs. |
          | `attachments` | array | | References to uploaded written consent files (max 20). See [`attachments[]`](#attachments). |
          | `purposes` | array | | Consent purposes in this interaction. See [`purposes[]`](#purposes). |
          | `privacyNotices` | array | | Privacy notices linked to the collection point. See [`privacyNotices[]`](#privacynotices). |
          | `geoLocation` | object | | Location where consent was provided. See [`geoLocation`](#geolocation). |

          ---

          ##### `consentString`
          | Field | Type | Description |
          |---|---|---|
          | `type` | enum | `GPP` · `TCF_EU` · `TCF_CANADA` |
          | `content` | string | Encoded consent string content. |

          ##### `receiptOptions[]`
          | Field | Type | Description |
          |---|---|---|
          | `option` | enum | `ClearExpiration` |
          | `purposes` | uuid[] | Purpose UUIDs to which the option applies. |

          ##### `source`
          | Field | Type | Description |
          |---|---|---|
          | `type` | enum | `WEB` · `MOBILE` · `CUSTOM` · `CTV` |
          | `content` | string | URL or identifier of the source. |
          | `purposeIds` | uuid[] | Purposes requiring consent for source capture. |

          ##### `parentPrimaryIdentifiers[]`
          | Field | Type | Description |
          |---|---|---|
          | `ParentIdentifier` | string | Identifier of the parent data subject. |
          | `AdditionalParentIdentifierTypes` | object | Additional parent identifier types as key-value pairs. |
          | `ConsentGivenBy` | boolean | Whether consent was given by the parent. |
          | `ParentTestDataSubject` | boolean | Whether the parent is a test data subject. |

          ##### `attachments[]`
          | Field | Type | Description |
          |---|---|---|
          | `id` | uuid | Unique identifier of the attachment. |

          ##### `purposes[]`
          | Field | Type | Description |
          |---|---|---|
          | `Id` | uuid | Purpose unique identifier. |
          | `Version` | long | Purpose version. |
          | `TransactionType` | enum | `PENDING` · `CONFIRMED` · `WITHDRAWN` · `EXPIRED` · `NOTGIVEN` · `EXTEND` · `OPT_OUT` · `HARD_OPT_OUT` · `NO_CHOICE` · `CHANGE_PREFERENCES` · `CANCEL` · `IMPLICIT`. API-type CPs only. |
          | `ExpiryDate` | datetime | Explicit expiry (e.g. `2025-10-15T10:30:00Z`). |
          | `Preferences` | array | Topic preferences. Each item: `TopicId` (uuid), `TransactionType` (`OPT_IN`\|`OPT_OUT`). Not supported on Web Form CPs. |
          | `CustomPreferences` | array | Purpose preference options. Each item: `Id` (uuid), `Options` (uuid[]), `Choices[]` → `OptionId` (uuid) + `TransactionType` (`OPT_IN`\|`OPT_OUT`). |
          | `PrivacyNotices` | array | Linked privacy notices. Each item: `Id` (uuid), `Version` (long), `MinorVersion` (long). |
          | `PurposeAttachments` | array | Uploaded files. Each item: `Id` (uuid). |
          | `PurposeNote` | array | Reason templates. Each item: `noteId` (uuid), `noteType` (enum: `UNSUBSCRIBE_REASON`), `noteLanguage` (ISO, e.g. `en-us`), `noteText` (string, max 500 chars). |

          ##### `privacyNotices[]`
          | Field | Type | Description |
          |---|---|---|
          | `Id` | uuid | Unique identifier of the linked privacy notice. |
          | `Version` | integer | Privacy notice version. |
          | `MinorVersion` | integer | Privacy notice minor version. |

          ##### `geoLocation`
          | Field | Type | Description |
          |---|---|---|
          | `country` | string | Country code where consent was provided. |
          | `state` | string | State code where consent was provided. |
          | `stateName` | string | State name where consent was provided. |
          | `purposeIds` | uuid[] | Purposes for which consent was provided at this location. |
    - Response Body

          ```json
          {
            "receipt": "<jwt>",
            "instantLinkToken": "<jwt-or-null>",
            "linkToken": "<token-or-null>"
          }
          ```

          | Field | Type | Description |
          |---|---|---|
          | `receipt` | string (JWT) | Record of the consent transaction. |
          | `instantLinkToken` | string | DS link token (JWT). Present only when `generateInstantLinkToken: true`. Expires after 12 months. Operates independently of Global Settings magic link creation. |
          | `linkToken` | string | Short DS link token. Present only when `shortLinkToken: true`. Can be appended to a Preference Center login URL. |
- Observation from API Documentation
    - Mixed of PascalCase and camelCase in the request payload
    - `shortLinkToken` field is used only for API type collection points which is not specified in api documentation
    - Max length of string fields is not specified
    - `linkToken` (in response) vs `shortLinkToken` (in request):  not clear mapping defined in api documentation.
    - 400 Bad Request: Errors code is not documented.
    - If Enable Parent-child relationship is enabled for a collection point, then the parentPrimaryIdentifiers field would be used else it would be ignored.
    - `generateInstantLinkToken` & `shortLinkToken` parameter is only supported for API-type collection points. Data is obtained from JWT `requestInformation` token claim parameter `moc`
    - Length Validations
      ├─ Identifier: MAX 700 chars ⚠️
      │   ├─ Custom Payload: MAX 4,000 chars ⚠️
      │   ├─ Data Elements (total): MAX 4,000 chars ⚠️
      │   ├─ Data Element Value: MAX 750 chars each ⚠️
      │   ├─ Multi-Select Data Elements: MAX 25 items ⚠️
      │   ├─ Purpose Note Text: MAX 500 chars ⚠️
      │   ├─ Language: ISO format
      │   ├─ Geolocation: Country/state codes
      │   ├─ Authentication: JWT validation
      │   └─ Transaction Type: Valid for CP type
        ```java
            // 1. Custom Payload (Line 976-981)
            if (customPayload.trim().length() > 4000) {
                throwException("customPayload exceeds 4000 characters");
            }

            // 2. Data Elements Total (Line 993-995)
            if (dsDataElements.toString().length() > N) {
                throwException("dsDataElements exceeds N characters");
            }

            // 3. Identifier (Line 1057-1059)
            if (identifier.length() > M) {
                throwException("Identifier exceeds character limit");
            }

            // 4. Data Element Value (Line 1049-1051)
            if (value.toString().length() > X) {
                throwException("dsDataElements Value exceeds X characters");
            }

            // 5. Purpose Note Text (Line 1140-1142)
            if (purposeNote.getNoteText().length() > 500) {
                throwException("Purpose note text exceeds 500 characters");
            }

            // 6. Multi-Select Data Element Value List (Line 1043-1045)
            if (valueList.size() > 25) {
                throwException("dsDataElements Value exceeds limit 25");
            }
        ```

### Call Flow

#### ds-request (ds-portal) — DSRequestController

Validates and builds response, then sends to Kafka:

```text
SEND TO KAFKA
│
├─ IF splitBulkImportEnabled && isBulkImport
│   → consent-receipts-bulkimport
│
├─ ELSE IF splitAnonymousEnabled && isAnonymous
│   → consent.consent-anonymous-receipts
│
├─ ELSE IF rulesEnabled
│   → consent.consent-rule-receipt-output
│
├─ ELSE IF dedicatedBulkTopic && isImport
│   → consent.consent-receipts-bulk
│
└─ ELSE (DEFAULT)
    → consent.consent-receipts
```

#### consent-transaction (main-app) — Kafka Consumers

```text
├─ [dsIngest] DsIngestConsumer
│   consumes: consent.consent-receipts
│   flag: onetrust.consenttransaction.toggle.consent.ingest.enabled
│   │
│   ├─ IF escapeLaneActivated for tenant
│   │   → PUBLISH to consent-receipt-escape-output
│   │       └─ [dsIngestEscape] DsIngestEscapeConsumer
│   │           flag: onetrust.consenttransaction.consent-receipt-escape.enabled
│   │           → IngestionService.ingestConsentReceiptInformation()
│   │
│   └─ ELSE → IngestionService.ingestConsentReceiptInformation()
│
├─ [consentAnonymousReceipts] ConsentAnonymousReceiptsConsumer
│   consumes: consent-anonymous-receipts
│   flag: onetrust.consenttransaction.toggle.anonymous.ingest.enabled
│         && onetrust.consent.split-anonymous.enabled
│   → IngestionService.ingestConsentReceiptInformation()
│
├─ [bulkDsIngest] BulkDsIngestConsumer
│   consumes: consent-receipts-bulkimport
│   flag: onetrust.consenttransaction.toggle.bulk.ingest.enabled
│   │
│   ├─ IF escapeLaneActivated → consent-receipt-escape-output
│   └─ ELSE → IngestionService.ingestConsentReceiptInformation()
│
└─ [dedicated bulk consumer]
    consumes: consent-receipts-bulk
    flag: onetrust.consent.dedicated-bulk-topic-consumer-enabled
    → IngestionService.ingestConsentReceiptInformation()
```

**IngestionService.ingestConsentReceiptInformation()**

```text
├─ 1. validateReceiptInformation()
│       └─ setSecurityContext, validateConsentString
├─ 2. validateAgentId()
├─ 3. skipNotGivenConsentsForCookie()
├─ 4. checkDuplicateReceipt (DS profile expiry guard)
├─ 5. transactionService.createTransactionsAndPublishEvent()
│   ├─ CREATE transactions in SQL DB
│   └─ PUBLISH → {env}.consent.consent.datasubject-profiles
│       │
│       ├─ [processDatasubjectUpdate] DatasubjectUpdateConsumer   (consentmanager)
│       │   → updates DS profile in SQL
│       │
│       └─ [processBulkDataSubjectUpdate] BulkDatasubjectUpdateConsumer  (consentmanager)
│           → bulk DS profile updates
│
└─ 6. receiptService.publishReceiptStoreMessage()
    │
    ├─ PUBLISH → consent-receiptjwt-output
    │   └─ [consentReceiptStorage] ConsentReceiptStorageConsumer
    │       flag: onetrust.consenttransaction.toggle.storage.ingest.enabled
    │       → ConsentReceiptStorageProcessor
    │           → ReceiptStorageService.storeReceipt()
    │               → Azure Blob Storage
    │
    ├─ PUBLISH → consentReceiptCosmos topic
    │   └─ [consentReceiptCosmos] ConsentReceiptCosmosConsumer
    │       flag: onetrust.consenttransaction.toggle.cosmos.enabled
    │             && onetrust.consenttransaction.toggle.cosmos.ingest.enabled
    │       → ConsentReceiptCosmosProcessor
    │           → Cosmos DB (DataSubject document)
    │
    └─ PUBLISH → consent-receiptjwt-reporting-output  [optional]
        → Reporting pipeline
```

**Key Outbound Topics from consent-transaction**

| Topic | Producer | Consumer |
|-------|----------|----------|
| `consent-datasubject-profile` | `TransactionProducer` | ds-preference-cache |
| `consent-datasubject-profile-bulk` | `TransactionBulkProducer` | ds-preference-cache (bulk) |
| `consent-receipt-escape-output` | `ConsentReceiptEscapeProducer` | DsIngestEscapeConsumer (self) |
| `consent-receiptjwt-output` | `ReceiptService` | ConsentReceiptStorageConsumer |
| `consent-cosmosmigration-output` | `CosmosMigrationService` | Cosmos migration pipeline |
| `consent-tracker-output` | `ConsentReceiptTrackingProducer` | Receipt tracking |

#### consentmanager (main-app) — DatasubjectUpdateConsumer

```text
[DatasubjectUpdateConsumer] (processDatasubjectUpdate)
consumes: {env}.consent.consent.datasubject-profiles
flag: onetrust.consenttransaction.toggle.consent.ingest.enabled
│
├─ IF escapeLaneActivated → profile-escape-event-output
│       └─ [DataSubjectEscapeConsumer] → re-ingested after escape
│
└─ TransactionCreatedDspUpdateProcessor.process()
    │
    ├─ IF isGenerateEventOnlyRequest
    │   → dspUpdateProcessorService.processDatasubjectForDownstreamEvents()
    │
    └─ ELSE → DspUpdateProcessorService.processDatasubjectProfileUpdate()
        ├─ 1. convertToSQLDateAndUpdate()
        ├─ 2. additionalIdentifierService.processProfileUpdateDtoPayload()
        ├─ 3. collectionPointService.findByGuidAndVersion()
        ├─ 4. dataSubjectService.getOrCreateWithLinkToken()
        │       → CREATE/GET DataSubject in SQL DB
        ├─ 5. dataSubjectService.update()
        │       → UPDATE DataSubject in SQL DB
        ├─ 6. createOrUpdateDataSubjectProfile()  [per transaction]
        │       → UPSERT DataSubjectProfile in SQL DB
        ├─ 7. sendAuditEvents()  [if !daisyChainRemoved]
        │       → DataSubjectAuditService.trackDataSubjectProfileUpdate()
        ├─ 8. dsCacheSyncService.migrateDataSubjectProfile()
        │       └─ PUBLISH → {env}.consent.consent.ds-cache-sync
        │                       └─ consumed by ds-preference-cache ↓
        ├─ 9. dataSubjectUpdateService.sendUpdateEvent()
        │       │
        │       ├─ IF isBulkImport && dedicatedBulkTopic
        │       │   → DataSubjectUpdatedBulkProducer
        │       │       → {env}.consent.consent.datasubjects-bulk
        │       │
        │       └─ ELSE → DataSubjectUpdatedProducer
        │                   → {env}.consent.consent.datasubjects
        │                       └─ consumed by integrations / webhooks
        │
        └─ 10. publishAdditionalIdentifierMergeRequest()  [if additionalIdentifiers present]
```

#### consentmanager (main-app) — DataSubjectUpdateCosmosParallelConsumer

```text
[DataSubjectUpdateCosmosParallelConsumer]
consumes: {env}.consent.consent.datasubject-profiles
└─ TransactionCreatedDspUpdateCosmosProcessor.process()
    └─ CosmosDspUpdateProcessorServiceImpl.processDataSubjectProfileUpdate()
        │
        ├─ 1. additionalIDService.processProfileUpdateDtoPayload()
        │       └─ REST GET /v4/datasubjects/additional-id/primary
        │               → consent-data-manager
        │               → CosmosDataSubjectDataServiceImpl.getPrimaryDsInfoForAdditionalId()
        │               → Cosmos DB (read existing DS for additional identifier)
        │
        ├─ 2. createOrUpdateLinkedIdentityGroupForParentIdentifiers()
        │       └─ REST POST /v1/datasubjects/details
        │               → consent-data-manager
        │               → CosmosDataSubjectDataServiceImpl.getDataSubjectProfileDetail()
        │               → Cosmos DB (read existing parent DS doc)
        │
        ├─ 3. ConsentStringUtil.processConsentStringForDataSubjectCosmos()
        │       └─ REST POST /v4/datasubjects/consentstrings
        │               → consent-data-manager
        │               → DataSubjectController.createOrUpdateConsentStringDocument()
        │               → Cosmos DB (write consent string document)
        │
        └─ 4. saveDataSubjectToCosmos()  ← THE MAIN WRITE
                └─ REST PUT /v4/datasubjects/{dataSubjectId}
                        → consent-data-manager
                        → DataSubjectController.updateDataSubjectCosmosDocuments()
                        → CosmosDataSubjectDataServiceImpl.createOrUpdateDsDocuments()
                        → Cosmos DB (write full DS document including:
                                    - DataSubject
                                    - DataSubjectProfiles (per purpose)
                                    - AccessTokens (if updateAccessToken=true)
                                    - LinkTokens (if updateLinkToken=true)
                                    - LinkedIdentityGroup (if updateLig=true))
```

**REST API Role Summary**

| Step | Method | Endpoint | Purpose |
|------|--------|----------|---------|
| Read | `GET` | `/v4/datasubjects/additional-id/primary` | Resolve additional identifier → primary DS |
| Read | `POST` | `/v1/datasubjects/details` | Fetch existing parent DS Cosmos doc |
| Write | `POST` | `/v4/datasubjects/consentstrings` | Upsert consent string document |
| Write | `PUT` | `/v4/datasubjects/{id}` | Full DS + profiles + tokens → Cosmos DB |

#### ds-preference-cache

```text
├─ [dsCacheSync] DsPreferenceSyncConsumer
│   consumes: {env}.consent.consent.ds-cache-sync
│   flag: onetrust.datasubject.preference.sync.enabled
│   │
│   ├─ IF escapeLaneActivated → ds-cache-sync-escape-output
│   │       └─ [DsPreferenceSyncEscapeConsumer] → re-ingested after escape
│   │
│   ├─ DsCacheSyncProcessor.processMessage()
│   │       → WRITE DataSubject profile to Cosmos DB
│   │
│   └─ DataSubjectUpdateProcessor.processMessage()
│           → process DS profile update metadata
│
└─ [dataSubjectReceipts] DataSubjectsReducedLatencyConsumer
    consumes: {env}.consent.consent.receipts  ← direct from ds-request (reduced latency path)
    flag: onetrust.datasubject.cache.ingest.enabled
    → DataSubjectsBlobPreferenceService.writeDataSubjectPreferences()
    → WRITE DS preferences to Blob Storage
```

**Key Topic Map**

| From | Topic | To |
|------|-------|----|
| consent-transaction | `{env}.consent.consent.datasubject-profiles` | consentmanager |
| consent-transaction | `{env}.consent.consent.datasubject-profiles` | consentmanager (bulk) |
| consentmanager | `{env}.consent.consent.ds-cache-sync` | ds-preference-cache |
| consentmanager | `{env}.consent.consent.datasubjects` | integrations/webhooks |
| ds-request (direct) | `{env}.consent.consent.receipts` | ds-preference-cache (reduced latency) |


## Data Subject Groups (Linked Identity Groups)

### Concept

Data Subject Groups (internally **Linked Identity Groups / LIG**) establish a **parent-child relationship** between data subjects for enhanced identity management.

Key behaviours:
- A **parent** data subject can provide consent on behalf of **child** data subjects within the same group.
- Granular preferences are maintained per individual data subject, but can be viewed and managed together.
- When a parent acts on behalf of a child, the child's activity log records: *"Parent Data Subject X made changes on behalf of Child Data Subject Y"*.
- A group can have **multiple parents**; if a group already exists with the same parent, children are added to the existing group rather than creating a new one.
- A data subject can belong to **multiple groups** simultaneously (tracked via `Other Linked Groups` count).
- Groups can be created programmatically via a Collection Point / Preference Center or manually in the platform UI.

## Anonymous vs Cross Device vs Identified Consent
### 1. Anonymous Cookie Consent

**What it is**  
Consent captured at browser/device level when the user is not identified (no login / stable user identifier).

**Typical characteristics**
- Tied to an anonymous identifier (cookie ID, device/browser token)
- Mostly for regulatory compliance (e.g. cookie banner choices)
- Very high volume and lower business value than identified consents
- Mainly used for aggregated analytics and compliance records, not per-user preference management

### 2. Cross Device Consent (CRO)

**What it is**  
Consent/preferences for a user that need to be synced across multiple devices and apps, using a non-anonymous identifier (e.g. login ID, email, customer ID).

**Typical characteristics**
- User is identified, and you want a single consent profile shared across:
  - Different devices (mobile, desktop, tablet)
  - Different properties (apps/sites in the same ecosystem)
- These are expressive consents/preferences that impact the experience and must stay consistent
- Implemented via the cross-device APIs (e.g. GET preferences by data subject identifier) as described in:
  - Cross Device Consent
  - Cross-Domain and Cross-Device Consent

**How it differs from plain anonymous consent**
- **Anonymous**: stays on one browser/device unless you do special URL-decoration tricks
- **Cross device**: stored against an identified profile, can be read and enforced anywhere the user logs in

### 3. Identified User Consent

**What it is**  
Consent captured for a known, uniquely identifiable person ("data subject"), usually for higher-risk or higher-value processing.


**Typical characteristics**

- Linked to a data subject profile (user ID, email, other identifiers)

- Includes consents like:

  - Acceptance for specific purposes (e.g. medical trials, marketing channels)

  - Legal/contractual consents requiring tight auditing

- Considered highest value because:

  - It is strongly tied to an identifiable individual

  - It is heavily used for compliance/audit, withdrawal, data subject rights flows

- Backed by transactional storage (Cosmos, etc.) with strong consistency, as described in the re-architecture docs: Consent Platform Re-architecture
Consent Platform Re-architecture


**Relationship to Cross Device**

- Cross Device Consents are a subtype/use case of identified consents:

  - Both are for identified users.

  - Cross device adds the "sync across devices / properties" requirement and specific APIs.

  - In the architecture page they even share Kafka topic, though handled by different workloads.


### Very Short Summary

- **Anonymous Cookie Consent**: Unknown user, cookie/device-level, mostly for compliance & stats
- **Cross Device Consent**: Known user, consent profile that must sync across devices/apps; uses authenticated APIs
- **Identified User Consent**: Known user, broad set of high-value consents (e.g. medical, marketing, data processing), full auditability; cross-device is one specialized pattern within this

Known user, consent profile that must sync across devices/apps; uses authenticated APIs.


### Storage Model

| Layer         | Entity / Table                                            | Key Fields                                                                                                                |
|---------------|-----------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| **Cosmos DB** | `CosmosLinkedIdentityGroup` (container per partition key) | `linkedIdentityGroupId`, `identifierHash`, `name`, `role` (PARENT/CHILD), `isPrimary`, `addedDate`, `createdDate`, `type` |
| **Azure SQL** | `consent.linkedidentitygroup`                             | `id`, `name`, `tenantId`, `createdDate`                                                                                   |
| **Azure SQL** | `consent.linkedidentitygroupdatasubject`                  | `linkedIdentityGroupId`, `dataSubjectId`, `role`, `isPrimary`, `addedDate`                                                |

### How Groups Are Written

Groups are created or updated as part of the **full DS document write** inside `consent-data-manager`:

```
consentmanager → PUT /v4/datasubjects/{id}  (updateLig=true)
  → CosmosDataSubjectDataServiceImpl.createOrUpdateDsDocuments()
  → writes CosmosLinkedIdentityGroup document into Cosmos DB
```

The `parentPrimaryIdentifiers[]` field in the receipt creation request (`POST /request/v1/consentreceipts`) triggers the parent-child link when the Collection Point has the **Enable Parent-child relationship** setting enabled.

### Read / Query Patterns

| Use Case | Predicate Fields | Cosmos Container |
|---|---|---|
| Get groups for a given data subject | `identifierHash = ?` [+ `linkedIdentityGroupId?`] | `CosmosLinkedIdentityGroup` |
| List all members of a group | `linkedIdentityGroupId = ?` ORDER BY `type`, `addedDate` | `CosmosLinkedIdentityGroup` |
| List all groups (admin/UI) | paginated [+ `name = ?`] ORDER BY `type`, `createdDate` | `CosmosLinkedIdentityGroup` |
| Dual-routed (consentmanager v2) | `id = ?` OR paginated | `consent.linkedidentitygroup` OR `CosmosLinkedIdentityGroup` |
 
---

## Public API → Predicate Params → Azure SQL + Cosmos Targets

> **Legend:**
> - 🔀 Dual-routed — same URL hits SQL or Cosmos based on tenant feature flag (`isConsentV4DataServiceFtEnabled`)
> - 🗄️ Azure SQL only (consentmanager legacy path)
> - ☁️ Cosmos only (consent-data-manager v4 path)
> - `*` = mandatory parameter

---

### Data Subject APIs

| # | Public API | Key Predicate / Filter Params | 🗄️ Azure SQL — Table & WHERE | ☁️ Cosmos — Container & WHERE |
|---|---|---|---|---|
| 1 | `GET /v4/datasubjects` | `fromDate`*, `toDate`*; sort: `lastModifiedDate`/`createdDate` | — | `CosmosDataSubject` WHERE `lastModifiedDate >= ? AND <= ?` ORDER BY `type`, `lastModifiedDate`/`createdDate` |
| 2 | `GET /v4/datasubjects/basic-details` | header: `identifier`* | — | `CosmosDataSubject` WHERE `identifierHash = ?` |
| 3 | `GET /v4/datasubjects/details` | header: `identifier`*; `includeConsentGroups?`, `includeAttachments?`, `includeNotices?`, `includeConsentStrings?`, `isDNCInclude?` | — | `CosmosDataSubject` WHERE `identifierHash = ?` + `CosmosDataSubjectProfile` WHERE `identifierHash = ?` |
| 4 | `GET /v4/datasubjects/ds-profiles` | header: `identifier`*; sort: `lastUpdatedDate` | — | `CosmosDataSubjectProfile` WHERE `identifierHash = ?` ORDER BY `type`, `lastUpdatedDate` |
| 5 | `GET /v4/datasubjects/profiles` | `updatedSince`*, `updatedUntil`*; `collectionPointId?`, `purposeId?`, `status?`; sort: `lastUpdatedDate` | — | `CosmosDataSubjectProfile` WHERE `lastUpdatedDate >= ? AND <= ?` [+ `collectionPointId`, `id`=purposeId, `status`] ORDER BY `type`, `lastUpdatedDate` |
| 6 | `GET /v4/datasubjects/profiles/{purposeGuid}` | header: `identifier`*; path: `purposeGuid`* | — | `CosmosDataSubjectProfile` WHERE `identifierHash = ?` AND `id = purposeGuid` |
| 7 | `GET /v4/datasubjects/unordered` | `fromDate`*, `toDate`* | — | `CosmosDataSubject` WHERE `lastModifiedDate >= ? AND <= ?` (feed-range, no ORDER BY) |
| 8 | `GET /v4/datasubjects/profiles/unordered` | `updatedSince`*, `updatedUntil`*; `collectionPointId?`, `purposeId?`, `status?` | — | `CosmosDataSubjectProfile` WHERE `lastUpdatedDate >= ? AND <= ?` [+ optional filters] (feed-range, no ORDER BY) |
| 9 | `GET /v1/datasubjects/profiles` *(consentmanager)* | header: `identifier?`, `dataElementName?`, `dataElementValue?`; query: `since?`, `updatedSince?`, `toDate?`, `purposeGuid?`, `collectionPointGuid?`, `collectionPointName?`, `linkedIdentityGroupId?`, `isDNCInclude?`, `includeGeolocation?` | 🔀 `consent.datasubject` JOIN `consent.datasubject_profile` JOIN `consent.datasubjectelement` WHERE `identifierHash`, `updateAt`/`createDt` range, `purposeGuid`, `collectionPointGuid`, `dataElements.name`/`valueHash` ORDER BY `updateAt`, `id` | 🔀 `CosmosDataSubject` + `CosmosDataSubjectProfile` WHERE `identifierHash`, `lastModifiedDate` range, `purposes.guid`, `collectionPointGuid`, `dataElements.name`/`hashValue` |
| 10 | `GET /v2/datasubjects` *(consentmanager)* | header: `identifier?`, `dataElementName?`, `dataElementValue?`; query: `updatedSince?`, `updatedUntil?`, `id?`, `language?`, `isDNCInclude?` | 🔀 `consent.datasubject` WHERE `identifierHash`, `updateAt` range, `id`, `language` | 🔀 `CosmosDataSubject` WHERE `identifierHash`, `lastModifiedDate` range, `dataSubjectId`, `language` |
| 11 | `POST /v2/datasubjects/search` *(consentmanager)* | header: `identifier?`; body: `updatedSince?`, `updatedUntil?`, `id?`, `identifier?`, `dataElements[]{name,value}?`, `language?`, `orgIds?` | 🔀 `consent.datasubject` JOIN `consent.datasubject_profile` JOIN `consent.datasubjectelement` WHERE `identifierHash`, `updateAt` range, `dataElements.name`/`valueHash`, `language` | 🔀 `CosmosDataSubject` WHERE `identifierHash`, `lastModifiedDate` range, `dataSubjectId`, `dataElements.name`/`hashValue`, `language` |

---

### Link Token APIs

| # | Public API | Key Predicate / Filter Params | 🗄️ Azure SQL — Table & WHERE | ☁️ Cosmos — Container & WHERE |
|---|---|---|---|---|
| 12 | `GET /v1/linktokens` *(consentmanager)* | query: `since?`, `until?`; header: `identifier?`; sort: `id`/`tokenId`/`expiryDate`/`createdDate` | 🗄️ `consent.emaillinktoken` WHERE `createDt >= ? AND <= ?` [+ `dataSubject.id` if identifier given] ORDER BY `expiryDate`, `id` | — |
| 13 | `GET /v4/linktokens` *(consent-api)* | `fromDate`*, `toDate`*; sort: `expiryDate` | — | ☁️ `CosmosDataSubject` WHERE `linkTokens[].createDate >= ? AND <= ?` ORDER BY `type`, `expiryDate` |
| 14 | `GET /v4/datasubjects/linktokens` | header: `identifier`* | — | ☁️ `CosmosDataSubject` WHERE `identifierHash = ?` (extracts nested `linkTokens[]`) |

---

### Receipt APIs

| # | Public API | Key Predicate / Filter Params | 🗄️ Azure SQL — Table & WHERE | ☁️ Cosmos — Container & WHERE |
|---|---|---|---|---|
| 15 | `GET /v1/receipt-list` *(consentmanager)* | header: `identifier`* | 🗄️ Receipt/transaction SQL tables WHERE `identifierHash = ?` | — |
| 16 | `GET /v1/receipts` *(consentmanager)* | header: `identifier`*; `includeNotgiven?` | 🗄️ Receipt/transaction SQL tables WHERE `identifierHash = ?` | — |
| 17 | `GET /v1/receipts/{id}` *(consentmanager)* | path: `id`*; `includeNotgiven?`, `includeConsentStrings?` | 🗄️ Receipt/transaction SQL tables WHERE `id = ?` | — |
| 18 | `POST /v2/receipts` *(consent-api)* | header: `identifier?`, `dataElementName?`, `dataElementValue?`; query: `collectionPointGuid?`, `receiptId?`, `purposeGuid?`, `organizationId?`, `fromDate?`, `toDate?`, `includeArchived?`, `includeConsentStrings?`; sort: `consentCreationDate` | 🗄️ SQL receipt tables **only when `includeArchived=true`** (receipts past 90-day TTL) | ☁️ `CosmosReceipt` WHERE `identifierHash` (from `identifier`), `collectionPointUUID`, `id` (from `receiptId`), `purposes.guid`, `consentCreationDate >= ? AND <= ?` — **primary path** |
| 19 | `GET /v2/preferences` | *(not detailed — separate preferences service)* | — | — |

---

### Linked Identity Group APIs

| # | Public API | Key Predicate / Filter Params | 🗄️ Azure SQL — Table & WHERE | ☁️ Cosmos — Container & WHERE |
|---|---|---|---|---|
| 20 | `GET /v4/linkedidentitygroups` | header: `identifier`*; query: `linkedIdentityGroupId?` | — | ☁️ `CosmosLinkedIdentityGroup` WHERE `identifierHash = ?` [+ `linkedIdentityGroupId`] |
| 21 | `GET /v4/linkedidentitygroups/{dataSubjectGroupId}/members` | path: `dataSubjectGroupId`* | — | ☁️ `CosmosLinkedIdentityGroup` WHERE `linkedIdentityGroupId = ?` ORDER BY `type`, `addedDate` |
| 22 | `GET /v4/groups` | header: `groupName?`; sort: `createdDate` | — | ☁️ `CosmosLinkedIdentityGroup` paginated [+ WHERE `name = ?`] ORDER BY `type`, `createdDate` |
| 23 | `GET /v2/linkedidentitygroups` *(consentmanager)* | pagination; `groupName?` | 🔀 `consent.linkedidentitygroup` JOIN `consent.linkedidentitygroupdatasubject` | 🔀 `CosmosLinkedIdentityGroup` paginated |
| 24 | `GET /v2/linkedidentitygroups/{linkedIdentityGroupId}` *(consentmanager)* | path: `linkedIdentityGroupId`*; `displayOrganizations?` | 🔀 `consent.linkedidentitygroup` WHERE `id = ?` | 🔀 `CosmosLinkedIdentityGroup` WHERE `linkedIdentityGroupId = ?` |

---

### Attachment APIs

| # | Public API | Key Predicate / Filter Params | 🗄️ Azure SQL | ☁️ Cosmos — Container & WHERE |
|---|---|---|---|---|
| 25 | `GET /v1/datasubjects/{identifier}/attachments` | path: `identifier`* | — | ☁️ `CosmosDataSubject.dsAttachments[]` WHERE `identifierHash = ?` |
| 26 | `GET /v1/attachments/{attachmentId}` | path: `attachmentId`*; header: `identifier?` | — | ☁️ `CosmosDataSubject.dsAttachments[]` WHERE `dsAttachments[].id = ?` [+ `identifierHash`] |

---

### UI-Based Use Cases → API + Storage Mapping

| UI Use Case | Filters Used | Backing API | Internal Target |
|---|---|---|---|
| **DataSubject List Page** | Identifier, Purpose, DataElement name+value, IdentifierType, CollectionPoint, LastUpdatedDate, TestDataSubject, PurposeOrg | API #9 `GET /v1/datasubjects/profiles` + API #10/#11 `v2/datasubjects[/search]` | 🔀 `consent.datasubject` + `consent.datasubject_profile` + `consent.datasubjectelement` OR `CosmosDataSubject` |
| **DataSubject Details Page** | identifier (from list selection) | API #3 `GET /v4/datasubjects/details` | ☁️ `CosmosDataSubject` + `CosmosDataSubjectProfile` WHERE `identifierHash = ?` |
| **DS Profiles / Purpose List** | identifier, purposeOrg filter | API #9 `GET /v1/datasubjects/profiles` | 🔀 `consent.datasubject_profile` OR `CosmosDataSubjectProfile` WHERE `identifierHash = ?` |
| **Linked Identity Group List** | GroupName | API #22 `GET /v4/groups` or API #23 `GET /v2/linkedidentitygroups` | ☁️/🔀 `CosmosLinkedIdentityGroup` [+ `name = ?`] |
| **LIG Details + Members** | `linkedIdentityGroupId` | API #21 `GET /v4/linkedidentitygroups/{id}/members` + API #24 | ☁️/🔀 `CosmosLinkedIdentityGroup` WHERE `linkedIdentityGroupId = ?` |
| **Receipt List Page** | identifier, collectionPointGuid, purposeGuid, fromDate, toDate, organizationId | API #18 `POST /v2/receipts` | ☁️ `CosmosReceipt` WHERE `identifierHash`, `collectionPointUUID`, `purposes.guid`, date range (+ SQL for `includeArchived=true`) |

---

## Public API Reference

> **Base URL:** `https://{hostname}` (tenant-specific OneTrust hostname)
> **Source:** [developer.onetrust.com](https://developer.onetrust.com/onetrust/reference)

Detailed reference for each public-facing consent API. Grouped by domain.

---

### Receipt Write APIs

#### POST /request/v1/consentreceipts — Create Consent Receipt
- **Ref:** https://developer.onetrust.com/onetrust/reference/createconsentreceiptusingpost
- **Purpose:** Create a consent receipt from any Collection Point (API-type, web form, etc.). Records the data subject's consent transaction.
- **Key Notes:**
  - Requires a valid Collection Point JWT in `requestInformation`.
  - `test=true` cannot be reverted to `false` via API.
  - Max 10 purposes recommended; absolute max 20.
  - `generateInstantLinkToken` and `shortLinkToken` are mutually exclusive; API-type CPs only.
  - Parent-child LIG linking via `parentPrimaryIdentifiers[]` — CP must have "Enable Parent-child relationship" enabled.
  - No data-type validation — invalid data is silently dropped.
- **Key Request Fields:** `requestInformation` (JWT), `identifier`, `identifierType`, `purposes[]`, `dsDataElements`, `customPayload`, `additionalIdentifiers`, `geoLocation`, `consentString` (GPP/TCF).
- **Response:** `{ receipt: JWT, instantLinkToken?, linkToken? }`
- **Length Limits:** identifier ≤ 700 chars; customPayload ≤ 4,000 chars total; dsDataElements ≤ 4,000 chars total; per-value ≤ 750 chars; multi-select ≤ 25 items; purposeNote ≤ 500 chars.

#### POST /request/v1/consentreceipts (bulk) — Create Consent Receipts in Bulk
- **Ref:** https://developer.onetrust.com/onetrust/reference/createbulkconsentreceiptusingpost
- **Purpose:** Optimized endpoint for bulk importing large numbers of consent receipts simultaneously.
- **Key Notes:**
  - **Rate limit:** 3,000 calls/minute; 3,000,000 receipts/day.
  - Response times vary with batch size — implement appropriate timeouts.
  - Same CP JWT setup requirements as the single receipt endpoint.
  - Max 10 purposes per receipt recommended; 20 absolute max.
- **Use Case:** Bulk historical imports, migration of consent data from legacy systems.

#### POST /request/v1/consentreceipts (identified) — Create Identified Consent Receipt
- **Ref:** https://developer.onetrust.com/onetrust/reference/createidentifiedconsentreceiptusingpost
- **Purpose:** Create consent receipts specifically for identified data subjects using non-cookie collection points.
- **Key Notes:**
  - Requires an explicit `identifier` in the request payload.
  - Creates a **persistent** consent record tied to the data subject's profile — manageable over time via a Preference Center.
  - Use `additionalIdentifiers` to link multiple identifiers to the same data subject profile.
  - Ideal for CRM-style identified consent, authenticated user consent, marketing opt-in/out.

---

### Data Subject Read APIs (v4 — Cosmos-backed)

These are the high-performance v4 APIs backed by Cosmos DB. Require `isConsentV4DataServiceFtEnabled` tenant flag.

#### GET /v4/datasubjects — Get List of Data Subjects
- **Ref:** https://developer.onetrust.com/onetrust/reference/getdatasubjectsv4
- **Purpose:** Retrieve data subjects last updated within a specified date range.
- **Key Notes:** Max date range: 7 days. Required params: `fromDate`, `toDate`. Sort: `lastModifiedDate` or `createdDate`.
- **Storage:** `CosmosDataSubject` WHERE `lastModifiedDate >= ? AND <= ?`

#### GET /v4/datasubjects/basic-details — Get Data Subject Basic Details
- **Ref:** https://developer.onetrust.com/onetrust/reference/getdatasubjectbasicdetailsv4
- **Purpose:** Retrieve a data subject's basic details (created date, last transaction date, data elements) by identifier.
- **Key Notes:** Identifier passed in **request header**. Lightweight — no full purpose/profile details.
- **Storage:** `CosmosDataSubject` WHERE `identifierHash = ?`

#### GET /v4/datasubjects/details — Get Data Subject Full Details
- **Ref:** https://developer.onetrust.com/onetrust/reference/getdatasubjectdetailsv4
- **Purpose:** Retrieve complete details for a specific data subject — basic details, all purposes, and email link tokens.
- **Key Notes:** Identifier in **request header**. Optional flags: `includeConsentGroups`, `includeAttachments`, `includeNotices`, `includeConsentStrings`, `isDNCInclude`.
- **Storage:** `CosmosDataSubject` + `CosmosDataSubjectProfile` WHERE `identifierHash = ?`

#### GET /v4/datasubjects/{identifier}/profiles — Get All Purpose Details for a Data Subject
- **Ref:** https://developer.onetrust.com/onetrust/reference/getallprofilesbydatasubjectv4
- **Purpose:** All purposes a specific data subject has interacted with — status, last transaction date, consent date, purpose preferences (topics, custom prefs).
- **Storage:** `CosmosDataSubjectProfile` WHERE `identifierHash = ?`

#### GET /v4/datasubjects/{identifier}/profiles/{purposeId} — Get Specific Purpose Details for a Data Subject
- **Ref:** https://developer.onetrust.com/onetrust/reference/getdatasubjectprofilev4
- **Purpose:** Consent details for a **single specific purpose** for a data subject — last transaction date, consent date, preferences.
- **Storage:** `CosmosDataSubjectProfile` WHERE `identifierHash = ?` AND `id = purposeId`

#### GET /v4/datasubjects/profiles/unordered — Get Optimized Unsorted DS Profiles (All Data Subjects)
- **Ref:** https://developer.onetrust.com/onetrust/reference/getdatasubjectprofilesunorderedv4
- **Purpose:** High-performance bulk retrieval of purpose details updated in a date range across **all** data subjects, with no guaranteed ordering.
- **Key Notes:**
  - Max date range: 7 days. Results are **unsorted**.
  - Supports **bookmark-based pagination** for consistent page traversal.
  - **More flexible rate limits** than the ordered `GET /v4/datasubjects/profiles`.
  - Prefer this for large-scale bulk exports or integrations where sort order is irrelevant.
- **Storage:** `CosmosDataSubjectProfile` paginated by `lastModifiedDate` range (feed-range, no ORDER BY)

#### GET /v4/datasubjects/unordered — Get Optimized Unsorted List of Data Subjects
- **Ref:** https://developer.onetrust.com/onetrust/reference/getdatasubjectsunorderedv4
- **Purpose:** High-performance bulk retrieval of data subjects updated in a date range, unsorted.
- **Key Notes:** Max date range: 7 days. Unsorted. Bookmark pagination. More flexible rate limits than `GET /v4/datasubjects`.
- **Storage:** `CosmosDataSubject` paginated by `lastModifiedDate` range (feed-range, no ORDER BY)

---

### Data Subject Delete APIs

#### DELETE /v4/datasubjects/ttl — Delete Data Subject (TTL-based)
- **Ref:** https://developer.onetrust.com/onetrust/reference/deletedatasubjectusingttl
- **Purpose:** Initiate TTL-based deletion of an entire data subject record. Deletion is **asynchronous** via Cosmos DB TTL.
- **Use Case:** GDPR right to erasure (right to be forgotten) — full data subject deletion.

#### DELETE /v4/datasubjects/purposes/ttl — Delete Purposes from Data Subject (TTL-based)
- **Ref:** https://developer.onetrust.com/onetrust/reference/deletepurposefromdatasubjectsusingttl
- **Purpose:** TTL-based deletion of **specific purposes** from a data subject rather than the entire record.
- **Use Case:** Purpose-level erasure — e.g. withdraw and delete a specific marketing consent purpose.

---

### Data Subject Merge API

#### POST /v1/datasubjects/merge — Merge / Deduplicate Data Subjects
- **Ref:** https://developer.onetrust.com/onetrust/reference/mergedatasubjectsusingpost
- **Purpose:** Merge multiple data subject records into a single primary record. All transactions and profile history are consolidated.
- **Key Notes:**
  - Data subjects in `additionalIdentifiers` are **deleted** after merging.
  - Existing transactions for `additionalIdentifiers` are converted to `primaryIdentifier`.
  - Data elements take the **most recently updated value** across all merged identifiers.
  - Receipts remain under the identifier from which they were originally generated.
  - Merged profile uses the magic link of the **surviving (primary)** data subject.
  - May affect consent status — review Transaction Types and Purpose Statuses docs for impact.
- **Use Case:** Resolving duplicate accounts, identity resolution after data migration.

---

### Legacy / v1 Read APIs

#### GET /v1/datasubjects/profiles — Get List of Data Subjects (v1)
- **Ref:** https://developer.onetrust.com/onetrust/reference/getdatasubjectprofileusingget
- **Purpose:** Full data subject list with data elements, purposes, topics, custom preferences, collection point interactions, and receipt IDs.
- **Key Notes:**
  - ⚠️ **Always include `properties=ignoreCount`** — omitting it significantly degrades performance.
  - Use `properties` values to tune response: `linkTokens`, `ignoreCount`, `ignoreTopics`, `ignoreCustomPreferences`.
  - **Not designed for synchronous workflows** — not suitable as a real-time consent check.
  - Use `requestContinuation` from response for efficient multi-page pagination.
  - Only the **primary identifier** is supported for search/filtering.
  - FTC Do Not Call list updated once daily (not real-time).
- **Storage:** 🔀 Dual-routed — SQL (`consent.datasubject` + `consent.datasubject_profile`) or Cosmos (`CosmosDataSubject`)

---

### Public API Summary Table

| # | Method | Path | Title | Status | Backing Store |
|---|---|---|---|---|---|
| 1 | `POST` | `/request/v1/consentreceipts` | Create Consent Receipt | ✅ Active | Kafka → SQL + Cosmos |
| 2 | `POST` | `/request/v1/consentreceipts` (bulk) | Create Consent Receipts in Bulk | ✅ Active | Kafka → SQL + Cosmos |
| 3 | `POST` | `/request/v1/consentreceipts` (identified) | Create Identified Consent Receipt | ✅ Active | Kafka → SQL + Cosmos |
| 4 | `GET` | `/v4/datasubjects` | Get List of Data Subjects (v4) | ✅ Active | ☁️ Cosmos |
| 5 | `GET` | `/v4/datasubjects/basic-details` | Get Data Subject Basic Details | ✅ Active | ☁️ Cosmos |
| 6 | `GET` | `/v4/datasubjects/details` | Get Data Subject Full Details | ✅ Active | ☁️ Cosmos |
| 7 | `GET` | `/v4/datasubjects/{id}/profiles` | Get All Purposes for a Data Subject | ✅ Active | ☁️ Cosmos |
| 8 | `GET` | `/v4/datasubjects/{id}/profiles/{purposeId}` | Get Specific Purpose for a Data Subject | ✅ Active | ☁️ Cosmos |
| 9 | `GET` | `/v4/datasubjects/profiles/unordered` | Get Optimized Unsorted DS Profiles (all DS) | ✅ Active | ☁️ Cosmos |
| 10 | `GET` | `/v4/datasubjects/unordered` | Get Optimized Unsorted List of Data Subjects | ✅ Active | ☁️ Cosmos |
| 11 | `DELETE` | `/v4/datasubjects/ttl` | Delete Data Subject (TTL) | ✅ Active | ☁️ Cosmos TTL |
| 12 | `DELETE` | `/v4/datasubjects/purposes/ttl` | Delete Purposes from Data Subject (TTL) | ✅ Active | ☁️ Cosmos TTL |
| 13 | `POST` | `/v1/datasubjects/merge` | Merge / Deduplicate Data Subjects | ✅ Active | 🔀 SQL + Cosmos |
| 14 | `GET` | `/v1/datasubjects/profiles` | Get List of Data Subjects (v1) | ✅ Active | 🔀 SQL + Cosmos |
| 15 | `GET` | `/v1/datasubjects/purposes` | Get Purposes for a Data Subject (v1) | ⚠️ Deprecated → use /profiles | 🗄️ SQL |
| 16 | `GET` | `/v1/preferences` | Get Data Subject's Preferences (v1) | ⚠️ Deprecated Nov 2025 → use V2 | ☁️ Cosmos |
 