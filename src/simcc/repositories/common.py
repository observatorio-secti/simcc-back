from simcc.repositories import tools


def _format_websearch(sql_string):
    return sql_string.replace('%(', ':').replace(')s', '')


def build_common_filters(
    filters,
    table_alias='bp',
    year_col='year',
    researcher_id_col='researcher_id',
    distinct_col='title',
):
    params = {}
    filters_sql = []
    joins = {
        'departament': '',
        'group': '',
        'institution': '',
        'program': '',
        'researcher_production': '',
        'foment': '',
    }
    distinct_sql = ''

    if getattr(filters, 'term', None):
        filter_terms, term_params = tools.websearch_filter(
            f'{table_alias}.{distinct_col}', filters.term
        )
        params.update(term_params)
        filters_sql.append(_format_websearch(filter_terms))

    if getattr(filters, 'year', None):
        params['year'] = int(filters.year)
        filters_sql.append(f' AND {table_alias}.{year_col}::INT >= :year')

    if getattr(filters, 'type', None):
        params['type'] = filters.type.split(';')
        filters_sql.append(f' AND {table_alias}.type = ANY(:type)')

    if getattr(filters, 'dep_id', None) or getattr(
        filters, 'departament', None
    ):
        pass

    if getattr(filters, 'researcher_id', None):
        params['researcher_id'] = str(filters.researcher_id)
        filters_sql.append(
            f' AND {table_alias}.{researcher_id_col} = :researcher_id'
        )

    if getattr(filters, 'lattes_id', None):
        params['lattes_id'] = filters.lattes_id
        filters_sql.append(' AND r.lattes_id = :lattes_id')

    if getattr(filters, 'group_id', None) or getattr(filters, 'group', None):
        joins['group'] = """
            INNER JOIN research_group_researcher rgr ON rgr.researcher_id = r.id
            INNER JOIN research_group rg ON rg.id = rgr.research_group_id
        """
        if getattr(filters, 'group_id', None):
            params['group_id'] = filters.group_id
            filters_sql.append(' AND rgr.research_group_id = :group_id')
        if getattr(filters, 'group', None):
            params['group'] = filters.group.split(';')
            filters_sql.append(' AND rg.name = ANY(:group)')

    if getattr(filters, 'institution', None) or getattr(
        filters, 'institution_id', None
    ):
        joins['institution'] = (
            'INNER JOIN institution i ON r.institution_id = i.id'
        )
        if getattr(filters, 'institution', None):
            params['institution'] = filters.institution.split(';')
            filters_sql.append(' AND i.name = ANY(:institution)')
        if getattr(filters, 'institution_id', None):
            params['institution_id'] = filters.institution_id
            filters_sql.append(' AND i.id = :institution_id')

    if getattr(filters, 'graduate_program_id', None) or getattr(
        filters, 'graduate_program', None
    ):
        distinct_sql = 'DISTINCT'
        joins['program'] = f"""
            INNER JOIN graduate_program_researcher gpr ON gpr.researcher_id = {table_alias}.{researcher_id_col}
            INNER JOIN graduate_program gp ON gpr.graduate_program_id = gp.graduate_program_id
        """
        if getattr(filters, 'graduate_program_id', None):
            params['graduate_program_id'] = str(filters.graduate_program_id)
            filters_sql.append(
                ' AND gpr.graduate_program_id = :graduate_program_id'
            )
        if getattr(filters, 'graduate_program', None):
            params['graduate_program'] = filters.graduate_program.split(';')
            filters_sql.append(' AND gp.name = ANY(:graduate_program)')

    if getattr(filters, 'city', None) or getattr(filters, 'area', None):
        joins['researcher_production'] = (
            f'LEFT JOIN researcher_production rp ON rp.researcher_id = {table_alias}.{researcher_id_col}'
        )
        if getattr(filters, 'city', None):
            params['city'] = filters.city.split(';')
            filters_sql.append(' AND rp.city = ANY(:city)')
        if getattr(filters, 'area', None):
            params['area'] = filters.area.replace(' ', '_').split(';')
            filters_sql.append(' AND rp.great_area_ && :area')

    if getattr(filters, 'modality', None):
        distinct_sql = 'DISTINCT'
        joins['foment'] = (
            f'INNER JOIN foment f ON f.researcher_id = {table_alias}.{researcher_id_col}'
        )
        params['modality'] = filters.modality.split(';')
        filters_sql.append(' AND f.modality_name = ANY(:modality)')

    if getattr(filters, 'graduation', None):
        params['graduation'] = filters.graduation.split(';')
        filters_sql.append(' AND r.graduation = ANY(:graduation)')

    filter_pagination = ''
    if getattr(filters, 'page', None) and getattr(filters, 'lenght', None):
        filter_pagination = _format_websearch(
            tools.pagination(filters.page, filters.lenght)
        )

    if getattr(filters, 'distinct', None) == '1':
        distinct_sql = f'DISTINCT ON ({table_alias}.{distinct_col})'

    return {
        'params': params,
        'filters_sql': ''.join(filters_sql),
        'joins': joins,
        'distinct_sql': distinct_sql,
        'filter_pagination': filter_pagination,
    }
