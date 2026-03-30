from pydantic import BaseModel


class AnalysisSummaryResponse(BaseModel):
    days: int
    total_pages: int
    total_features: int
    recent_updates: int
