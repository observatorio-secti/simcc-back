from typing import Optional

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description='Page number')
    lenght: int = Field(100, ge=1, le=500, description='Items per page')

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.lenght

    @property
    def limit(self) -> int:
        return self.lenght


class SortParams(BaseModel):
    sort_by: Optional[str] = Field(None, description='Field to sort by')
    sort_order: Optional[str] = Field(
        'asc', pattern='^(asc|desc)$', description='Sort order (asc or desc)'
    )
