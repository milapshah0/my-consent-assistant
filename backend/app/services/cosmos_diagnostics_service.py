from __future__ import annotations

import json
import time
import uuid
from typing import Any

from azure.cosmos import CosmosClient, DatabaseProxy
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError
from fastapi import HTTPException

from app.config import get_settings
from app.schemas.cosmos import (
    CosmosContainerInfoResponse,
    CosmosDiagnosticsRequest,
    CosmosDiagnosticsResponse,
    CosmosIndexSummaryResponse,
    CosmosInsertMetricsResponse,
    CosmosInsertScenarioRequest,
    CosmosOperationMetricsResponse,
    CosmosSizeEstimateResponse,
)

SHARED_CONTAINERS = {
    "consent-datasubjects",
    "consent-tokens",
    "consent-linked-identities",
}


class CosmosDiagnosticsService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def list_containers(self) -> list[CosmosContainerInfoResponse]:
        database = self._get_database_client()
        containers: list[CosmosContainerInfoResponse] = []
        for item in database.list_containers():
            partition_key = item.get("partitionKey") or {}
            containers.append(
                CosmosContainerInfoResponse(
                    id=item.get("id", ""),
                    partition_key_paths=partition_key.get("paths", []),
                    default_ttl=item.get("defaultTtl"),
                    analytical_storage_ttl=item.get("analyticalStorageTtl"),
                )
            )
        containers.sort(key=lambda container: container.id)
        return containers

    def run_diagnostics(
        self, request: CosmosDiagnosticsRequest
    ) -> CosmosDiagnosticsResponse:
        database = self._get_database_client()
        container = database.get_container_client(request.container_name)
        container_properties = container.read()
        partition_key_paths = (container_properties.get("partitionKey") or {}).get(
            "paths", []
        )
        partition_key_field = partition_key_paths[0] if partition_key_paths else None
        query_text = request.query_text.strip()
        if not query_text:
            raise HTTPException(status_code=400, detail="Query text is required")

        if request.logical_type and " where " not in query_text.lower():
            query_text = f"{query_text} WHERE c.type = @logicalType"
        elif request.logical_type:
            query_text = f"{query_text} AND c.type = @logicalType"

        parameters: list[dict[str, Any]] = []
        if request.logical_type:
            parameters.append({"name": "@logicalType", "value": request.logical_type})

        query_header_store: dict[str, str] = {}
        started_at = time.perf_counter()
        try:
            items_iterable = container.query_items(
                query=query_text,
                parameters=parameters,
                partition_key=request.partition_key_value,
                enable_cross_partition_query=True,
                max_item_count=request.max_items,
                populate_query_metrics=True,
                populate_index_metrics=True,
                response_hook=lambda headers, _: query_header_store.update(headers),
            )
            sample_documents = list(items_iterable)
        except TypeError:
            items_iterable = container.query_items(
                query=query_text,
                parameters=parameters,
                enable_cross_partition_query=True,
                max_item_count=request.max_items,
                populate_query_metrics=True,
                populate_index_metrics=True,
                response_hook=lambda headers, _: query_header_store.update(headers),
            )
            sample_documents = list(items_iterable)
        except CosmosHttpResponseError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)

        index_summary = self._build_index_summary(container_properties)
        size_estimate = self._build_size_estimate(sample_documents)
        insert_metrics = None
        scenario_insert_metrics: list[CosmosInsertMetricsResponse] = []
        if request.perform_sample_insert and sample_documents:
            insert_metrics = self._measure_sample_insert(
                container=container,
                source_document=sample_documents[0],
                partition_key_field=partition_key_field,
                override_partition_key_value=request.partition_key_value,
                cleanup_after_insert=request.cleanup_after_insert,
            )
        if request.insert_scenarios:
            scenario_insert_metrics = [
                self._measure_insert_scenario(
                    container=container,
                    scenario=scenario,
                    partition_key_field=partition_key_field,
                    default_logical_type=request.logical_type,
                    default_cleanup_after_insert=request.cleanup_after_insert,
                )
                for scenario in request.insert_scenarios
            ]

        return CosmosDiagnosticsResponse(
            container_name=request.container_name,
            database_name=self.settings.cosmos_database_name,
            logical_type=request.logical_type,
            query_text=query_text,
            partition_key_field=partition_key_field,
            partition_key_value=request.partition_key_value,
            result_count=len(sample_documents),
            query_metrics=CosmosOperationMetricsResponse(
                request_charge=self._read_float_header(
                    query_header_store, "x-ms-request-charge"
                ),
                duration_ms=duration_ms,
                activity_id=query_header_store.get("x-ms-activity-id"),
                query_metrics=self._read_metric_value(
                    query_header_store,
                    "x-ms-documentdb-query-metrics",
                    "x-ms-query-metrics",
                ),
                index_metrics=self._read_metric_value(
                    query_header_store,
                    "x-ms-documentdb-index-metrics",
                    "x-ms-index-metrics",
                    "x-ms-cosmos-index-utilization",
                ),
                status_code=self._read_int_header(
                    query_header_store, "x-ms-status-code"
                ),
            ),
            insert_metrics=insert_metrics,
            insert_scenarios=scenario_insert_metrics,
            index_summary=index_summary,
            size_estimate=size_estimate,
            sample_documents=sample_documents,
            tuning_recommendations=self._build_tuning_recommendations(
                request=request,
                query_request_charge=self._read_float_header(
                    query_header_store, "x-ms-request-charge"
                ),
                index_summary=index_summary,
                size_estimate=size_estimate,
                result_count=len(sample_documents),
            ),
        )

    def _measure_sample_insert(
        self,
        container: Any,
        source_document: dict[str, Any],
        partition_key_field: str | None,
        override_partition_key_value: str | None,
        cleanup_after_insert: bool,
    ) -> CosmosInsertMetricsResponse:
        new_document = json.loads(json.dumps(source_document))
        new_id = f"diag-{uuid.uuid4()}"
        new_document["id"] = new_id
        new_document["diagnosticsRunId"] = new_id
        partition_key_value = (
            override_partition_key_value
            or self._extract_partition_key_value(source_document, partition_key_field)
        )
        if partition_key_field and partition_key_value is not None:
            self._assign_partition_key_value(
                new_document, partition_key_field, partition_key_value
            )

        if partition_key_field and partition_key_value is None:
            return CosmosInsertMetricsResponse(
                inserted=False,
                cleaned_up=False,
                item_id=new_id,
                source_item_id=str(source_document.get("id", "")) or None,
                source_item_type=str(source_document.get("type", "")) or None,
                partition_key_field=partition_key_field,
                partition_key_value=None,
                request_charge=0.0,
                delete_request_charge=0.0,
                create_response_headers={},
                delete_response_headers={},
                inserted_document=new_document,
                status="partition_key_missing",
                error_message="Unable to derive partition key value for the sampled document",
            )

        create_headers: dict[str, str] = {}
        delete_headers: dict[str, str] = {}
        try:
            container.create_item(
                body=new_document,
                response_hook=lambda headers, _: create_headers.update(headers),
            )
        except CosmosHttpResponseError as exc:
            return CosmosInsertMetricsResponse(
                inserted=False,
                cleaned_up=False,
                item_id=new_id,
                source_item_id=str(source_document.get("id", "")) or None,
                source_item_type=str(source_document.get("type", "")) or None,
                partition_key_field=partition_key_field,
                partition_key_value=None
                if partition_key_value is None
                else str(partition_key_value),
                request_charge=0.0,
                delete_request_charge=0.0,
                create_response_headers=dict(create_headers),
                delete_response_headers={},
                inserted_document=new_document,
                status="insert_failed",
                error_message=str(exc),
            )

        cleaned_up = False
        if cleanup_after_insert:
            try:
                container.delete_item(
                    item=new_id,
                    partition_key=partition_key_value,
                    response_hook=lambda headers, _: delete_headers.update(headers),
                )
                cleaned_up = True
            except (CosmosHttpResponseError, CosmosResourceNotFoundError):
                cleaned_up = False

        return CosmosInsertMetricsResponse(
            purpose="sample_clone",
            inserted=True,
            cleaned_up=cleaned_up,
            item_id=new_id,
            source_item_id=str(source_document.get("id", "")) or None,
            source_item_type=str(source_document.get("type", "")) or None,
            partition_key_field=partition_key_field,
            partition_key_value=None
            if partition_key_value is None
            else str(partition_key_value),
            request_charge=self._read_float_header(
                create_headers, "x-ms-request-charge"
            ),
            delete_request_charge=self._read_float_header(
                delete_headers, "x-ms-request-charge"
            ),
            create_response_headers=dict(create_headers),
            delete_response_headers=dict(delete_headers),
            inserted_document=new_document,
            status="ok"
            if cleaned_up or not cleanup_after_insert
            else "inserted_cleanup_failed",
            error_message=None,
        )

    def _measure_insert_scenario(
        self,
        container: Any,
        scenario: CosmosInsertScenarioRequest,
        partition_key_field: str | None,
        default_logical_type: str | None,
        default_cleanup_after_insert: bool,
    ) -> CosmosInsertMetricsResponse:
        new_document = json.loads(json.dumps(scenario.payload))
        new_id = str(new_document.get("id") or f"diag-{uuid.uuid4()}")
        new_document["id"] = new_id

        effective_logical_type = scenario.logical_type or default_logical_type
        if effective_logical_type and "type" not in new_document:
            new_document["type"] = effective_logical_type

        partition_key_value = (
            scenario.partition_key_value
            or self._extract_partition_key_value(new_document, partition_key_field)
        )
        if partition_key_field and partition_key_value is not None:
            self._assign_partition_key_value(
                new_document, partition_key_field, partition_key_value
            )

        if partition_key_field and partition_key_value is None:
            return CosmosInsertMetricsResponse(
                purpose=scenario.purpose,
                inserted=False,
                cleaned_up=False,
                item_id=new_id,
                source_item_id=None,
                source_item_type=str(new_document.get("type", "")) or None,
                partition_key_field=partition_key_field,
                partition_key_value=None,
                request_charge=0.0,
                delete_request_charge=0.0,
                create_response_headers={},
                delete_response_headers={},
                inserted_document=new_document,
                status="partition_key_missing",
                error_message="Insert scenario is missing a partition key value",
            )

        create_headers: dict[str, str] = {}
        delete_headers: dict[str, str] = {}
        try:
            container.create_item(
                body=new_document,
                response_hook=lambda headers, _: create_headers.update(headers),
            )
        except CosmosHttpResponseError as exc:
            return CosmosInsertMetricsResponse(
                purpose=scenario.purpose,
                inserted=False,
                cleaned_up=False,
                item_id=new_id,
                source_item_id=None,
                source_item_type=str(new_document.get("type", "")) or None,
                partition_key_field=partition_key_field,
                partition_key_value=None
                if partition_key_value is None
                else str(partition_key_value),
                request_charge=0.0,
                delete_request_charge=0.0,
                create_response_headers=dict(create_headers),
                delete_response_headers={},
                inserted_document=new_document,
                status="insert_failed",
                error_message=str(exc),
            )

        cleanup_after_insert = (
            scenario.cleanup_after_insert
            if scenario.cleanup_after_insert is not None
            else default_cleanup_after_insert
        )
        cleaned_up = False
        if cleanup_after_insert:
            try:
                container.delete_item(
                    item=new_id,
                    partition_key=partition_key_value,
                    response_hook=lambda headers, _: delete_headers.update(headers),
                )
                cleaned_up = True
            except (CosmosHttpResponseError, CosmosResourceNotFoundError):
                cleaned_up = False

        return CosmosInsertMetricsResponse(
            purpose=scenario.purpose,
            inserted=True,
            cleaned_up=cleaned_up,
            item_id=new_id,
            source_item_id=None,
            source_item_type=str(new_document.get("type", "")) or None,
            partition_key_field=partition_key_field,
            partition_key_value=None
            if partition_key_value is None
            else str(partition_key_value),
            request_charge=self._read_float_header(
                create_headers, "x-ms-request-charge"
            ),
            delete_request_charge=self._read_float_header(
                delete_headers, "x-ms-request-charge"
            ),
            create_response_headers=dict(create_headers),
            delete_response_headers=dict(delete_headers),
            inserted_document=new_document,
            status="ok"
            if cleaned_up or not cleanup_after_insert
            else "inserted_cleanup_failed",
            error_message=None,
        )

    def _build_index_summary(
        self, container_properties: dict[str, Any]
    ) -> CosmosIndexSummaryResponse:
        indexing_policy = container_properties.get("indexingPolicy") or {}
        vector_indexes = indexing_policy.get("vectorIndexes") or []
        return CosmosIndexSummaryResponse(
            included_path_count=len(indexing_policy.get("includedPaths") or []),
            excluded_path_count=len(indexing_policy.get("excludedPaths") or []),
            composite_index_count=len(indexing_policy.get("compositeIndexes") or []),
            spatial_index_count=len(indexing_policy.get("spatialIndexes") or []),
            vector_index_count=len(vector_indexes),
            indexing_mode=indexing_policy.get("indexingMode"),
            automatic=indexing_policy.get("automatic"),
        )

    def _build_size_estimate(
        self, documents: list[dict[str, Any]]
    ) -> CosmosSizeEstimateResponse:
        if not documents:
            return CosmosSizeEstimateResponse()
        sizes = [
            len(json.dumps(document, default=str).encode("utf-8"))
            for document in documents
        ]
        largest = max(sizes)
        average = round(sum(sizes) / len(sizes))
        limit = 2 * 1024 * 1024
        return CosmosSizeEstimateResponse(
            sample_count=len(documents),
            average_document_bytes=average,
            largest_document_bytes=largest,
            two_mb_limit_bytes=limit,
            remaining_bytes_to_two_mb_for_largest_document=max(limit - largest, 0),
        )

    def _build_tuning_recommendations(
        self,
        request: CosmosDiagnosticsRequest,
        query_request_charge: float,
        index_summary: CosmosIndexSummaryResponse,
        size_estimate: CosmosSizeEstimateResponse,
        result_count: int,
    ) -> list[str]:
        recommendations: list[str] = []
        if request.container_name in SHARED_CONTAINERS and not request.logical_type:
            recommendations.append(
                "This is a shared multi-type container. Add a logical type filter so RU reflects the targeted document family rather than the full container."
            )
        if not request.partition_key_value:
            recommendations.append(
                "Run the same query with a partition key value when possible. Cross-partition fan-out is often the fastest way to increase RU."
            )
        if query_request_charge >= 20:
            recommendations.append(
                "The query request charge is high. Compare this query with and without extra predicates to isolate which filter is causing the RU jump."
            )
        if index_summary.included_path_count > 10:
            recommendations.append(
                "The container has many included index paths. Review whether some write-heavy fields can be excluded from indexing to lower write RU."
            )
        if size_estimate.largest_document_bytes >= int(1.5 * 1024 * 1024):
            recommendations.append(
                "At least one sampled document is approaching the 2 MB document limit. Consider splitting large payload fields or moving archival blobs out of the item."
            )
        if result_count == 0:
            recommendations.append(
                "No rows were returned. Validate the container, type, and partition key first before comparing RU across query variants."
            )
        if not recommendations:
            recommendations.append(
                "Use this run as a baseline, then compare RU after adding a partition key filter, a logical type filter, or narrower projected fields."
            )
        return recommendations

    def _get_database_client(self) -> DatabaseProxy:
        if (
            not self.settings.cosmos_endpoint
            or not self.settings.cosmos_key
            or not self.settings.cosmos_database_name
        ):
            raise HTTPException(
                status_code=400,
                detail="Cosmos diagnostics is not configured. Set COSMOS_ENDPOINT, COSMOS_KEY, and COSMOS_DATABASE_NAME.",
            )
        client = CosmosClient(
            self.settings.cosmos_endpoint, credential=self.settings.cosmos_key
        )
        return client.get_database_client(self.settings.cosmos_database_name)

    @staticmethod
    def _extract_partition_key_value(
        document: dict[str, Any], partition_key_field: str | None
    ) -> Any:
        if not partition_key_field:
            return None
        field_parts = partition_key_field.lstrip("/").split("/")
        value: Any = document
        for part in field_parts:
            if not isinstance(value, dict) or part not in value:
                return None
            value = value[part]
        return value

    @staticmethod
    def _assign_partition_key_value(
        document: dict[str, Any], partition_key_field: str, value: Any
    ) -> None:
        field_parts = partition_key_field.lstrip("/").split("/")
        current: dict[str, Any] = document
        for part in field_parts[:-1]:
            nested = current.get(part)
            if not isinstance(nested, dict):
                nested = {}
                current[part] = nested
            current = nested
        current[field_parts[-1]] = value

    @staticmethod
    def _read_header(headers: dict[str, str], *keys: str) -> str | None:
        for key in keys:
            value = headers.get(key)
            if value:
                return value
        return None

    @staticmethod
    def _read_metric_value(
        headers: dict[str, Any], *keys: str
    ) -> str | dict[str, Any] | list[Any] | None:
        for key in keys:
            value = headers.get(key)
            if value is not None:
                return value
        return None

    @staticmethod
    def _read_float_header(headers: dict[str, str], key: str) -> float:
        value = headers.get(key)
        try:
            return float(value) if value is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _read_int_header(headers: dict[str, str], key: str) -> int | None:
        value = headers.get(key)
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None
