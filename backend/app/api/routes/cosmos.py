from fastapi import APIRouter

from app.schemas.cosmos import (
    CosmosAssistantRequest,
    CosmosAssistantResponse,
    CosmosContainerInfoResponse,
    CosmosDiagnosticsRequest,
    CosmosDiagnosticsResponse,
)
from app.services.cosmos_assistant_service import CosmosAssistantService
from app.services.cosmos_diagnostics_service import CosmosDiagnosticsService

router = APIRouter()
service = CosmosDiagnosticsService()
assistant_service = CosmosAssistantService()


@router.get("/containers")
async def get_cosmos_containers() -> dict[str, list[CosmosContainerInfoResponse]]:
    return {"items": service.list_containers()}


@router.post("/diagnostics/run", response_model=CosmosDiagnosticsResponse)
async def run_cosmos_diagnostics(
    payload: CosmosDiagnosticsRequest,
) -> CosmosDiagnosticsResponse:
    return service.run_diagnostics(payload)


@router.post("/assistant", response_model=CosmosAssistantResponse)
async def run_cosmos_assistant(
    payload: CosmosAssistantRequest,
) -> CosmosAssistantResponse:
    return await assistant_service.assist(payload)
