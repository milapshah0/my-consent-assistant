# Cosmos Container Flow

## Purpose

This document explains how Cosmos document types are mapped to containers in `consent-data-manager`, and how the same flow can be reused to build a diagnostics app for Cosmos.

## Key Finding

This codebase does **not** use one container per `type`.

Instead, it uses **one container per domain group**, and stores **multiple logical document types** inside the same container using the `type` field from `AbstractTypedCosmosDocument`.

So the effective design is:

- **One container to many document types**
- **Container chosen by entity class hierarchy / `@Container` annotation**
- **Logical record kind chosen by `type` field**

## Base Flow

### 1. Every typed Cosmos document carries a `type`

Base class:

- `server/src/main/java/com/onetrust/consent/datamanager/domain/cosmos/dto/AbstractTypedCosmosDocument.java`

Important field:

- `type`

This is the logical discriminator used in queries, deletes, and diagnostics.

### 2. Container is defined at the abstract container class level

The main abstract container classes are:

- `AbstractCosmosDataSubjectContainer`
- `AbstractCosmosTokenContainer`
- `AbstractCosmosLinkedIdentityGroupContainer`

Each of these is annotated with `@Container(...)`, which fixes the physical Cosmos container name.

### 3. Concrete entity classes inherit both container and type behavior

Each concrete entity:

- extends one abstract container class
- calls `super(<TYPE_CONSTANT>)`
- therefore gets:
  - physical container from inherited `@Container`
  - logical type from inherited `AbstractTypedCosmosDocument`

### 4. Runtime container lookup happens from the entity class

Example path:

- `AbstractFeedRangeProcessor.runSliceQuery(...)`
- uses `CosmosEntityInformation.getInstance(domainType).getContainerName()`
- then gets the actual container using `CosmosContainerInstanceFactory.getAsyncContainer(containerName)`

So at runtime, the input `domainType` determines the container.

### 5. Queries and deletes often further filter on `type`

Example:

- `CustomCosmosDataSubjectRepositoryImpl.deleteByIdentifierHash(...)`

This method accepts:

- `containerName`
- list of classes

And when the container is `consent-datasubjects`, it explicitly restricts deletion to selected document types using `type IN (...)`.

## Container Mapping

## Physical Containers

From `ConsentDataManagerConstant`:

- `consent-datasubjects`
- `consent-tokens`
- `consent-linked-identities`
- `consent-deletion-certificate`
- `consentstrings`

## Mapping: Container -> Types

### `consent-datasubjects`

Abstract base:

- `AbstractCosmosDataSubjectContainer`

Known logical types stored here:

- `DataSubject`
- `ConsentString`
- `Profile`
- `DataSubjectIdDictionary`
- `DataSubjectDeletionExcluded`
- `LinkedIdentityGroup`

Representative entities:

- `CosmosDataSubject`
- `CosmosDataSubjectConsentString`
- `CosmosDataSubjectProfile`
- `CosmosDataSubjectIdDictionary`
- `CosmosDataSubjectDeletionExclusion`
- `CosmosLinkedIdentityGroup`

Notes:

- Partitioning is entity-specific, commonly `identifierHash`
- Most operational queries also include `type`
- This is the main example of many logical types inside one container

### `consent-tokens`

Abstract base:

- `AbstractCosmosTokenContainer`

Known logical types stored here:

- `DataSubjectAccessToken`
- `EmailLinkToken`
- `LinkTokenDictionary`
- `AdditionalIdDictionary`

Representative entities:

- `CosmosDataSubjectAccessToken`
- `CosmosLinkTokenDictionary`
- additional token/dictionary entities extending `AbstractCosmosTokenContainer`

Notes:

- Shared indexing is optimized around token/date/type query patterns
- Token-related diagnostics should always show both container and type

### `consent-linked-identities`

Abstract base:

- `AbstractCosmosLinkedIdentityGroupContainer`

Known logical types stored here:

- `LinkedIdentityGroupDictionary`
- linked identity group variants that inherit this base

Representative entities:

- `CosmosLinkedIdentityGroupDictionary`
- `CosmosLinkedIdentityGroupV2`

Notes:

- This container is separate from the `LinkedIdentityGroup` type that is also referenced in `consent-datasubjects` deletion logic
- Diagnostics should distinguish carefully between similarly named types and storage locations

### Dedicated containers

These appear to be single-purpose containers based on entity-level `@Container` usage:

- `consent-deletion-certificate`
- `consentstrings`

Representative entities identified by search:

- `CosmosDeletionCertificate`
- `CosmosReceipt`

## How Container Resolution Works

## Decision Rule

If you need to determine where a document lives, do this in order:

### Step 1: Identify the concrete entity class

Examples:

- `CosmosDataSubject`
- `CosmosDataSubjectProfile`
- `CosmosDataSubjectAccessToken`
- `CosmosLinkTokenDictionary`

### Step 2: Walk up to the abstract parent class

Examples:

- `CosmosDataSubject` -> `AbstractCosmosDataSubjectContainer`
- `CosmosDataSubjectAccessToken` -> `AbstractCosmosTokenContainer`

### Step 3: Read the inherited `@Container(containerName = ...)`

That gives the physical Cosmos container.

### Step 4: Read the `super(<TYPE>)` call in the concrete class

That gives the logical `type` value stored in the document.

## Example Resolution

### Example A: `CosmosDataSubject`

- Parent: `AbstractCosmosDataSubjectContainer`
- Container: `consent-datasubjects`
- Type: `DataSubject`

### Example B: `CosmosDataSubjectProfile`

- Parent: `AbstractCosmosDataSubjectContainer`
- Container: `consent-datasubjects`
- Type: `Profile`

### Example C: `CosmosDataSubjectAccessToken`

- Parent: `AbstractCosmosTokenContainer`
- Container: `consent-tokens`
- Type: `DataSubjectAccessToken`

### Example D: `CosmosLinkTokenDictionary`

- Parent: `AbstractCosmosTokenContainer`
- Container: `consent-tokens`
- Type: `LinkTokenDictionary`

## Important Runtime Components

### `CosmosContainerInstanceFactory`

Path:

- `server/src/main/java/com/onetrust/consent/datamanager/framework/CosmosContainerInstanceFactory.java`

Responsibility:

- sets Cosmos context
- preprocesses request for the target container
- resolves database name via multi-tenant factory
- returns `CosmosAsyncContainer`

This is the right place to instrument diagnostics around:

- database name
- container name
- tenant context
- request lifecycle

### `AbstractFeedRangeProcessor`

Path:

- `server/src/main/java/com/onetrust/consent/datamanager/framework/AbstractFeedRangeProcessor.java`

Responsibility:

- derives container name from `domainType`
- runs query against a resolved async container
- processes diagnostics via `ResponseDiagnosticsProcessorImpl`

This is one of the best hooks for a diagnostics app because it already captures:

- query text
- container name
- continuation token behavior
- feed ranges
- response diagnostics

### Repository-level filtering

Example:

- `CustomCosmosDataSubjectRepositoryImpl`

Responsibility:

- builds Cosmos queries
- applies `type` filters
- performs delete/query operations against a specified container

For diagnostics, repository logging should capture:

- repository method name
- container name
- target classes
- `type` filters
- partition key values when present

## End-to-End Data Flow

Typical request flow:

1. Service decides which entity/repository to use
2. Repository or processor receives a concrete `domainType`
3. Entity metadata resolves the physical container name
4. Query is executed against that container
5. `type` is used to narrow to the logical document kind
6. Diagnostics are emitted from Cosmos response processing and application logging

## What a Cosmos Diagnostics App Should Show

For each Cosmos operation, display at least the following:

- **Operation name**
  - query, upsert, delete, read, feed-range query

- **Entity class**
  - concrete Java class used for the operation

- **Abstract container group**
  - data subject, token, linked identity, dedicated container

- **Physical container**
  - actual Cosmos container name

- **Logical type**
  - document `type` value

- **Partition key field/value**
  - for example `identifierHash`, `token`, or other entity-specific key

- **Query text / criteria**
  - SQL query or generated criteria

- **Tenant/database context**
  - resolved database name and context before execution

- **Diagnostics output**
  - request charge, latency, index metrics, query metrics, continuation token, feed range

- **Result summary**
  - number of documents returned/affected

## Recommended Diagnostics Model

A diagnostics event can use this shape:

```text
operationId
operationType
serviceMethod
repositoryMethod
entityClass
abstractContainerClass
containerName
documentType
partitionKeyField
partitionKeyValue
databaseName
tenantContext
queryText
criteriaSummary
requestCharge
latencyMs
continuationToken
feedRange
resultCount
status
errorMessage
```

## Recommended Build Strategy for the Diagnostics App

### Phase 1: Static mapping view

Build a screen that shows:

- container name
- entity classes in that container
- logical `type` values per entity
- partition key field per entity

This can be derived by scanning the same inheritance model used in this codebase.

### Phase 2: Runtime tracing

Instrument:

- `CosmosContainerInstanceFactory`
- `AbstractFeedRangeProcessor`
- custom repository implementations

Capture structured events for every Cosmos operation.

### Phase 3: Query explorer

Allow filtering by:

- container
- type
- identifier hash / token
- repository method
- time range
- tenant
- success/failure

### Phase 4: Anomaly detection

Highlight:

- unexpected type written to wrong container
- mismatched entity class vs container
- high RU queries
- repeated continuation token loops
- missing partition key filters
- cross-type deletes in shared containers

## Rules to Reuse in a Diagnostics App

Use these rules consistently:

### Rule 1

**Do not infer container from `type` alone.**

`type` is a logical discriminator, not the primary container selector.

### Rule 2

**Resolve container from the entity class hierarchy and `@Container`.**

### Rule 3

**Always record both container and type.**

In this codebase, either one alone is incomplete.

### Rule 4

**Treat shared containers as multi-type stores.**

Especially:

- `consent-datasubjects`
- `consent-tokens`
- `consent-linked-identities`

### Rule 5

**When diagnosing deletes, inspect both container and type filters.**

Shared-container delete logic may intentionally target only a subset of types.

## File References

- `server/src/main/java/com/onetrust/consent/datamanager/constant/ConsentDataManagerConstant.java`
- `server/src/main/java/com/onetrust/consent/datamanager/domain/cosmos/dto/AbstractTypedCosmosDocument.java`
- `server/src/main/java/com/onetrust/consent/datamanager/domain/cosmos/AbstractCosmosDataSubjectContainer.java`
- `server/src/main/java/com/onetrust/consent/datamanager/domain/cosmos/AbstractCosmosTokenContainer.java`
- `server/src/main/java/com/onetrust/consent/datamanager/domain/cosmos/AbstractCosmosLinkedIdentityGroupContainer.java`
- `server/src/main/java/com/onetrust/consent/datamanager/framework/CosmosContainerInstanceFactory.java`
- `server/src/main/java/com/onetrust/consent/datamanager/framework/AbstractFeedRangeProcessor.java`
- `server/src/main/java/com/onetrust/consent/datamanager/repository/cosmos/custom/impl/CustomCosmosDataSubjectRepositoryImpl.java`
- `server/src/main/java/com/onetrust/consent/datamanager/service/v4/impl/CosmosDataSubjectDataServiceImpl.java`

## Summary

The Cosmos storage model in this repository is best understood as:

- **physical container selected by entity/container class**
- **logical record kind selected by `type`**
- **many logical types can exist inside one physical container**

If you build a diagnostics app for Cosmos, the most important reusable diagnostic tuple is:

- **entity class**
- **container name**
- **type**
- **partition key**
- **query/operation diagnostics**
