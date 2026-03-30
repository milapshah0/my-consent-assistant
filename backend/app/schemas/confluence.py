from pydantic import BaseModel


class ConfluencePageResponse(BaseModel):
    id: str
    title: str
    excerpt: str
    space_key: str
    url: str
    author_name: str
