import re
from typing import Any, Dict, List, Set

from sqlalchemy import text

from simcc.core.dependencies import get_settings

settings = get_settings()


class BaseQuery:
    SUPPORTED_FILTERS: Set[str] = set()

    def __init__(self, session):
        self.session = session
        self.params: Dict[str, Any] = {}
        self.filters_sql: List[str] = []
        self.joins: Dict[str, str] = {}
        self.order_by: str = ''
        self.distinct_sql: str = ''
        self.pagination_sql: str = ''

    def _format_websearch(self, sql_string: str) -> str:
        return re.sub(r'%\(([^)]+)\)s', r':\1', sql_string)

    def apply_filters(self, filters: Any):
        if not filters:
            return
        for field in self.SUPPORTED_FILTERS:
            if isinstance(filters, dict):
                value = filters.get(field)
            else:
                value = getattr(filters, field, None)
            # Skip None AND empty strings to avoid errors from frontend
            if value is not None and value != str():
                method_name = f'_apply_{field}_filter'
                if hasattr(self, method_name):
                    getattr(self, method_name)(value)
                else:
                    print('filter_implementation_missing')

    def apply_pagination(self, pagination: Any):
        if (
            pagination
            and hasattr(pagination, 'offset')
            and hasattr(pagination, 'limit')
        ):
            self.pagination_sql = (
                f'OFFSET {pagination.offset} LIMIT {pagination.limit}'
            )

    async def execute(self):
        query = self.build_sql()
        result = await self.session.execute(text(query), self.params)
        return result.mappings().all()

    def build_sql(self) -> str:
        raise NotImplementedError('Subclasses must implement build_sql')
