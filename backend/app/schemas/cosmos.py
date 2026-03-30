from typing import Any

from pydantic import BaseModel, Field


class CosmosContainerInfoResponse(BaseModel):
    id: str
    partition_key_paths: list[str] = Field(default_factory=list)
    default_ttl: int | None = None
    analytical_storage_ttl: int | None = None


class CosmosDiagnosticsRequest(BaseModel):
    container_name: str
    query_text: str
    partition_key_value: str | None = None
    logical_type: str | None = None
    max_items: int = Field(default=10, ge=1, le=100)
    perform_sample_insert: bool = False
    cleanup_after_insert: bool = True
    insert_scenarios: list["CosmosInsertScenarioRequest"] = Field(default_factory=list)


class CosmosInsertScenarioRequest(BaseModel):
    purpose: str
    payload: dict[str, Any]
    partition_key_value: str | None = None
    logical_type: str | None = None
    cleanup_after_insert: bool | None = None


class CosmosIndexSummaryResponse(BaseModel):
    included_path_count: int = 0
    excluded_path_count: int = 0
    composite_index_count: int = 0
    spatial_index_count: int = 0
    vector_index_count: int = 0
    indexing_mode: str | None = None
    automatic: bool | None = None


class CosmosSizeEstimateResponse(BaseModel):
    sample_count: int = 0
    average_document_bytes: int = 0
    largest_document_bytes: int = 0
    two_mb_limit_bytes: int = 2 * 1024 * 1024
    remaining_bytes_to_two_mb_for_largest_document: int = 0


class CosmosOperationMetricsResponse(BaseModel):
    request_charge: float = 0.0
    duration_ms: float = 0.0
    activity_id: str | None = None
    query_metrics: str | dict[str, Any] | list[Any] | None = None
    index_metrics: str | dict[str, Any] | list[Any] | None = None
    status_code: int | None = None


class CosmosInsertMetricsResponse(BaseModel):
    purpose: str | None = None
    inserted: bool
    cleaned_up: bool
    item_id: str | None = None
    source_item_id: str | None = None
    source_item_type: str | None = None
    partition_key_field: str | None = None
    partition_key_value: str | None = None
    request_charge: float = 0.0
    delete_request_charge: float = 0.0
    create_response_headers: dict[str, Any] = Field(default_factory=dict)
    delete_response_headers: dict[str, Any] = Field(default_factory=dict)
    inserted_document: dict[str, Any] | None = None
    status: str
    error_message: str | None = None


class CosmosDiagnosticsResponse(BaseModel):
    container_name: str
    database_name: str
    logical_type: str | None = None
    query_text: str
    partition_key_field: str | None = None
    partition_key_value: str | None = None
    result_count: int
    query_metrics: CosmosOperationMetricsResponse
    insert_metrics: CosmosInsertMetricsResponse | None = None
    insert_scenarios: list[CosmosInsertMetricsResponse] = Field(default_factory=list)
    index_summary: CosmosIndexSummaryResponse
    size_estimate: CosmosSizeEstimateResponse
    sample_documents: list[dict[str, Any]] = Field(default_factory=list)
    tuning_recommendations: list[str] = Field(default_factory=list)


class CosmosAssistantRequest(BaseModel):
    action: str = Field(min_length=1, max_length=50)
    prompt: str = Field(min_length=1, max_length=4000)
    container_name: str
    logical_type: str | None = None
    partition_key_field: str | None = None
    partition_key_value: str | None = None
    current_query: str | None = None
    diagnostics_result: dict[str, Any] | None = None


class CosmosAssistantResponse(BaseModel):
    answer: str
    suggested_query: str | None = None
    follow_up_questions: list[str] = Field(default_factory=list)
