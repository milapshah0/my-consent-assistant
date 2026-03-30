from pydantic import BaseModel


class AhaFeatureResponse(BaseModel):
    id: str
    reference_num: str
    name: str
    status: str
    priority: str
    url: str
