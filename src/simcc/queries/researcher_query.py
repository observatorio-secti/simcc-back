from typing import Optional

from simcc.queries.base import BaseQuery
from simcc.repositories import tools

STOPWORDS = {
    'a',
    'agora',
    'ainda',
    'alguem',
    'algum',
    'alguma',
    'algumas',
    'alguns',
    'ampla',
    'amplas',
    'amplo',
    'amplos',
    'ante',
    'antes',
    'ao',
    'aos',
    'apos',
    'aquela',
    'aquelas',
    'aquele',
    'aqueles',
    'aquilo',
    'as',
    'ate',
    'atraves',
    'cada',
    'coisa',
    'coisas',
    'com',
    'como',
    'contra',
    'contudo',
    'da',
    'daquele',
    'daqueles',
    'das',
    'de',
    'dela',
    'delas',
    'dele',
    'deles',
    'depois',
    'desde',
    'dessa',
    'dessas',
    'desse',
    'desses',
    'desta',
    'destas',
    'deste',
    'destes',
    'deve',
    'devem',
    'devendo',
    'dever',
    'devera',
    'deverao',
    'deveria',
    'deveriam',
    'devia',
    'deviam',
    'disse',
    'disso',
    'disto',
    'dito',
    'diz',
    'dizem',
    'do',
    'dos',
    'e',
    'ela',
    'elas',
    'ele',
    'eles',
    'em',
    'enquanto',
    'entre',
    'era',
    'eram',
    'eramos',
    'essa',
    'essas',
    'esse',
    'esses',
    'esta',
    'estamos',
    'estao',
    'estas',
    'estava',
    'estavam',
    'estavamos',
    'este',
    'estes',
    'esteve',
    'estive',
    'estivemos',
    'estiver',
    'estivera',
    'estiveram',
    'estivereis',
    'estiverem',
    'estivermos',
    'estivesse',
    'estivessem',
    'estivessemos',
    'estou',
    'eu',
    'foi',
    'fomos',
    'for',
    'fora',
    'foram',
    'foramos',
    'forem',
    'formos',
    'fosse',
    'fossem',
    'fossemos',
    'fui',
    'grande',
    'grandes',
    'ha',
    'haja',
    'hajam',
    'hajamos',
    'hao',
    'haver',
    'havera',
    'haverao',
    'haveria',
    'haveriam',
    'havia',
    'haviam',
    'haviamos',
    'houve',
    'houvemos',
    'houver',
    'houvera',
    'houveram',
    'houverem',
    'houvermos',
    'houvesse',
    'houvessem',
    'houvessemos',
    'isso',
    'isto',
    'ja',
    'lhe',
    'lhes',
    'lo',
    'logo',
    'mais',
    'mas',
    'me',
    'mediante',
    'menos',
    'mesma',
    'mesmas',
    'mesmo',
    'mesmos',
    'meu',
    'meus',
    'minha',
    'minhas',
    'muito',
    'muita',
    'muitas',
    'muitos',
    'na',
    'nao',
    'naquela',
    'naquelas',
    'naquele',
    'naqueles',
    'nas',
    'nem',
    'no',
    'nos',
    'nossa',
    'nossas',
    'nosso',
    'nossos',
    'num',
    'numa',
    'o',
    'os',
    'ou',
    'outra',
    'outras',
    'outro',
    'outros',
    'para',
    'pela',
    'pelas',
    'pelo',
    'pelos',
    'pequena',
    'pequenas',
    'pequeno',
    'pequenos',
    'per',
    'perante',
    'pode',
    'pude',
    'podendo',
    'poder',
    'podera',
    'poderao',
    'poderiamos',
    'poderia',
    'poderiam',
    'podia',
    'podiam',
    'pois',
    'por',
    'porem',
    'porque',
    'posso',
    'pouca',
    'poucas',
    'pouco',
    'poucos',
    'primeiro',
    'primeiros',
    'propria',
    'proprias',
    'proprio',
    'proprios',
    'quais',
    'qual',
    'quando',
    'quanto',
    'quantos',
    'que',
    'quem',
    'sao',
    'se',
    'seja',
    'sejam',
    'sejamos',
    'sem',
    'sempre',
    'sendo',
    'sera',
    'serao',
    'serei',
    'seremos',
    'seria',
    'seriam',
    'seu',
    'seus',
    'si',
    'sido',
    'so',
    'sob',
    'sobre',
    'sua',
    'suas',
    'talvez',
    'tambem',
    'tampouco',
    'te',
    'tem',
    'tendo',
    'tenha',
    'tenham',
    'tenhamos',
    'tenho',
    'tens',
    'ter',
    'tera',
    'terao',
    'terei',
    'teremos',
    'teria',
    'teriam',
    'teu',
    'teus',
    'teve',
    'ti',
    'tinha',
    'tinham',
    'tinhamos',
    'tive',
    'tivemos',
    'tiver',
    'tivera',
    'tiveram',
    'tiverem',
    'tivermos',
    'tivesse',
    'tivessem',
    'tivéssemos',
    'toda',
    'todas',
    'todavia',
    'todo',
    'todos',
    'tu',
    'tua',
    'tuas',
    'tudo',
    'um',
    'uma',
    'umas',
    'uns',
    'vendo',
    'ver',
    'vez',
    'vindo',
    'vir',
    'voce',
    'voces',
    'vos',
    'vossa',
    'vossas',
    'vosso',
    'vossos',
    'vou',
    'about',
    'above',
    'after',
    'again',
    'against',
    'all',
    'am',
    'an',
    'and',
    'any',
    'are',
    'arent',
    'as',
    'at',
    'be',
    'because',
    'been',
    'before',
    'being',
    'below',
    'between',
    'both',
    'but',
    'by',
    'cant',
    'cannot',
    'could',
    'couldnt',
    'did',
    'didnt',
    'do',
    'does',
    'doesnt',
    'doing',
    'dont',
    'down',
    'during',
    'each',
    'few',
    'for',
    'from',
    'further',
    'had',
    'hadnt',
    'has',
    'hasnt',
    'have',
    'havent',
    'having',
    'he',
    'hed',
    'hell',
    'hes',
    'her',
    'here',
    'heres',
    'hers',
    'herself',
    'him',
    'himself',
    'his',
    'how',
    'hows',
    'id',
    'ill',
    'im',
    'ive',
    'if',
    'in',
    'into',
    'is',
    'isnt',
    'it',
    'its',
    'itself',
    'lets',
    'me',
    'more',
    'most',
    'mustnt',
    'my',
    'myself',
    'no',
    'nor',
    'not',
    'of',
    'off',
    'on',
    'once',
    'only',
    'or',
    'other',
    'ought',
    'our',
    'ours',
    'ourselves',
    'out',
    'over',
    'own',
    'same',
    'shant',
    'she',
    'shed',
    'shell',
    'shes',
    'should',
    'shouldnt',
    'so',
    'some',
    'such',
    'than',
    'that',
    'thats',
    'the',
    'their',
    'theirs',
    'them',
    'themselves',
    'then',
    'there',
    'theres',
    'these',
    'they',
    'theyd',
    'theyll',
    'theyre',
    'theyve',
    'this',
    'those',
    'through',
    'to',
    'too',
    'under',
    'until',
    'up',
    'very',
    'was',
    'wasnt',
    'we',
    'wed',
    'well',
    'were',
    'weve',
    'werent',
    'what',
    'whats',
    'when',
    'whens',
    'where',
    'wheres',
    'which',
    'while',
    'who',
    'whos',
    'whom',
    'why',
    'whys',
    'with',
    'wont',
    'would',
    'wouldnt',
    'you',
    'youd',
    'youll',
    'youre',
    'youve',
    'your',
    'yours',
    'yourself',
    'yourselves',
}


class ResearcherSearchQuery(BaseQuery):
    SUPPORTED_FILTERS = {
        'institution_id',
        'graduate_program_id',
        'researcher_id',
        'researcher_ids',
        'dep_id',
        'group_id',
        'lattes_id',
        'term',
        'terms',
        'institution',
        'graduate_program',
        'departament',
        'group',
        'city',
        'area',
        'modality',
        'graduation',
        'year',
        'type',
        'distinct',
    }

    def __init__(
        self,
        session,
        search_type: Optional[str] = None,
        name: Optional[str] = None,
    ):
        super().__init__(session)
        self.search_type = search_type
        self.name = name
        self.term_value = None
        self.year_value = None
        self.distinct_value = None
        # Default joins needed for the SELECT clause
        self.joins = {
            'institution': 'LEFT JOIN institution i ON i.id = r.institution_id',
            'researcher_production': 'LEFT JOIN researcher_production rp ON rp.researcher_id = r.id',
            'openalex_researcher': 'LEFT JOIN openalex_researcher opr ON opr.researcher_id = r.id',
        }

    def _apply_institution_id_filter(self, value):
        self.joins['institution'] = (
            'INNER JOIN institution i ON i.id = r.institution_id'
        )
        self.params['institution_id'] = value
        self.filters_sql.append(' AND i.id = :institution_id ')

    def _apply_institution_filter(self, value):
        self.joins['institution'] = (
            'INNER JOIN institution i ON i.id = r.institution_id'
        )
        self.params['institution'] = value.split(';')
        self.filters_sql.append(' AND i.name = ANY(:institution) ')

    def _apply_city_filter(self, value):
        # Keeps LEFT JOIN but adds filter
        self.params['city'] = value.split(';')
        self.filters_sql.append(' AND rp.city = ANY(:city) ')

    def _apply_area_filter(self, value):
        self.params['area'] = value.replace(' ', '_').split(';')
        self.filters_sql.append(' AND rp.great_area_ && :area ')

    def _apply_graduation_filter(self, value):
        self.params['graduation'] = value.split(';')
        self.filters_sql.append(' AND r.graduation = ANY(:graduation) ')

    def _apply_lattes_id_filter(self, value):
        self.params['lattes_id'] = value
        self.filters_sql.append(' AND r.lattes_id = :lattes_id ')

    def _apply_researcher_id_filter(self, value):
        self.params['researcher_id'] = str(value)
        self.filters_sql.append(' AND r.id = :researcher_id ')

    def _apply_researcher_ids_filter(self, value):
        self.params['researcher_ids'] = [str(v) for v in value]
        self.filters_sql.append(' AND r.id = ANY(:researcher_ids) ')

    def _apply_term_filter(self, value):
        self.term_value = value

    def _apply_terms_filter(self, value):
        self._apply_term_filter(value)

    def _apply_year_filter(self, value):
        self.year_value = int(value)

    def _apply_type_filter(self, value):
        self.type_value = value

    def _apply_distinct_filter(self, value):
        self.distinct_value = value

    def _apply_dep_id_filter(self, value):
        pass

    def _apply_departament_filter(self, value):
        pass

    def _apply_group_id_filter(self, value):
        self.joins['group'] = """
            INNER JOIN research_group_researcher rgr ON rgr.researcher_id = r.id
            INNER JOIN research_group rg ON rg.id = rgr.research_group_id
        """
        self.params['group_id'] = value
        self.filters_sql.append(' AND rgr.research_group_id = :group_id')

    def _apply_group_filter(self, value):
        self.joins['group'] = """
            INNER JOIN research_group_researcher rgr ON rgr.researcher_id = r.id
            INNER JOIN research_group rg ON rg.id = rgr.research_group_id
        """
        self.params['group'] = value.split(';')
        self.filters_sql.append(' AND rg.name = ANY(:group)')

    def _apply_graduate_program_id_filter(self, value):
        self.joins['program'] = """
            INNER JOIN graduate_program_researcher gpr ON gpr.researcher_id = r.id
            INNER JOIN graduate_program gp ON gpr.graduate_program_id = gp.graduate_program_id
        """
        self.params['graduate_program_id'] = str(value)
        self.filters_sql.append(
            ' AND gpr.graduate_program_id = :graduate_program_id'
        )

    def _apply_graduate_program_filter(self, value):
        self.joins['program'] = """
            INNER JOIN graduate_program_researcher gpr ON gpr.researcher_id = r.id
            INNER JOIN graduate_program gp ON gpr.graduate_program_id = gp.graduate_program_id
        """
        self.params['graduate_program'] = value.split(';')
        self.filters_sql.append(' AND gp.name = ANY(:graduate_program)')

    def _apply_modality_filter(self, value):
        self.joins['foment'] = 'INNER JOIN foment f ON f.researcher_id = r.id'
        self.params['modality'] = value.split(';')
        if value != '*':
            self.filters_sql.append(' AND f.modality_name = ANY(:modality)')

    def _build_inner_join(self) -> tuple[str, str]:
        inner_join = ''
        among_col = '0 AS among'

        if self.search_type == 'PARTICIPATION_EVENT':
            inner_join, among_col = self._build_event_join()
        elif self.search_type == 'AREA_SPECIALTY':
            among_col = self._build_area_specialty_filter()
        elif self.search_type in {
            'BOOK',
            'ARTICLE',
            'ABSTRACT',
            'PATENT',
            'BOOK_CHAPTER',
        }:
            inner_join, among_col = self._build_production_join()

        return inner_join, among_col

    def _build_event_join(self) -> tuple[str, str]:
        filter_terms = ''
        if self.term_value:
            filter_terms, term_params = tools.websearch_filter(
                'pe.event_name', self.term_value
            )
            self.params.update(term_params)
            filter_terms = self._format_websearch(filter_terms)

        filter_year = ''
        if self.year_value:
            self.params['year_pe'] = self.year_value
            filter_year = 'AND pe.year >= :year_pe'

        inner_join = f"""
            INNER JOIN (
                SELECT pe.researcher_id, COUNT(*) AS among
                FROM participation_events pe
                WHERE pe.type_participation IN ('Apresentação Oral', 'Conferencista', 'Moderador', 'Simposista')
                {filter_terms}
                {filter_year}
                GROUP BY researcher_id
            ) pe ON pe.researcher_id = r.id
        """
        return inner_join, 'pe.among'

    def _build_area_specialty_filter(self) -> str:
        if self.term_value:
            filter_terms, term_params = tools.websearch_filter(
                'rp.area_specialty', self.term_value
            )
            self.params.update(term_params)
            self.filters_sql.append(self._format_websearch(filter_terms))
        return '1 AS among'

    def _build_production_join(self) -> tuple[str, str]:
        if self.search_type == 'ABSTRACT':
            if self.term_value:
                filter_terms, term_params = tools.websearch_filter(
                    'r.abstract', self.term_value
                )
                self.params.update(term_params)
                self.filters_sql.append(self._format_websearch(filter_terms))
            return '', '0 AS among'

        table_name = (
            'patent'
            if self.search_type == 'PATENT'
            else 'bibliographic_production'
        )
        type_filter = (
            f"AND bp.type = '{self.search_type}'"
            if self.search_type != 'PATENT'
            else ''
        )
        term_col = 'p.title' if self.search_type == 'PATENT' else 'bp.title'
        year_col = (
            'p.development_year::INT'
            if self.search_type == 'PATENT'
            else 'bp.year_'
        )
        alias = 'p' if self.search_type == 'PATENT' else 'bp'

        filter_terms = ''
        if self.term_value:
            filter_terms, term_params = tools.websearch_filter(
                term_col, self.term_value
            )
            self.params.update(term_params)
            filter_terms = self._format_websearch(filter_terms)

        filter_year = ''
        if self.year_value:
            self.params['year_inner'] = self.year_value
            filter_year = f'AND {year_col} >= :year_inner'

        inner_join = f"""
            INNER JOIN (
                SELECT {alias}.researcher_id, COUNT(*) AS among
                FROM {table_name} {alias}
                WHERE 1 = 1 {type_filter}
                {filter_terms}
                {filter_year}
                GROUP BY researcher_id
            ) {alias} ON {alias}.researcher_id = r.id
        """
        return inner_join, f'{alias}.among'

    def build_sql(self) -> str:
        inner_join, among_col = self._build_inner_join()
        order_by = 'r.name'
        distinct_sql = ''

        if among_col != '0 AS among':
            order_by = 'among DESC'

        if self.name:
            name_filter, name_params = tools.names_filter('r.name', self.name)
            self.filters_sql.append(name_filter)
            self.params.update(name_params)

        if self.distinct_value == '1' or self.distinct_value == 1:
            distinct_sql = 'DISTINCT ON (r.id)'
            order_by = f'r.id, {order_by}'

        filters_sql = ' '.join(self.filters_sql)

        SCRIPT_SQL = f"""
            SELECT {distinct_sql}
                r.id, r.name, r.lattes_id, r.lattes_10_id, r.abstract, r.orcid,
                r.graduation, r.last_update AS lattes_update,
                REPLACE(rp.great_area, '_', ' ') AS area, rp.city,
                i.image AS image_university, i.name AS university,
                {among_col},
                COALESCE(rp.articles, 0) AS articles,
                COALESCE(rp.book_chapters, 0) AS book_chapters,
                COALESCE(rp.book, 0) AS book,
                COALESCE(rp.patent, 0) AS patent,
                COALESCE(rp.software, 0) AS software,
                COALESCE(rp.brand, 0) AS brand,
                COALESCE(opr.h_index, 0) AS h_index,
                COALESCE(opr.relevance_score, 0) AS relevance_score,
                COALESCE(opr.works_count, 0) AS works_count,
                COALESCE(opr.cited_by_count, 0) AS cited_by_count,
                COALESCE(opr.i10_index, 0) AS i10_index,
                opr.scopus,
                opr.openalex,
                r.classification, r.status, r.institution_id,
                r.abstract_ai, r.stars
            FROM researcher r
                {' '.join(self.joins.values())}
                {inner_join}
            WHERE 1 = 1
                AND r.status IS True
                {filters_sql}
            ORDER BY {order_by}
            {self.pagination_sql};
        """
        return SCRIPT_SQL


class ResearcherTermQuery(BaseQuery):
    SUPPORTED_FILTERS = {'researcher_id', 'dep_id', 'graduate_program_id'}

    def __init__(self, session):
        super().__init__(session)
        self.params['stopwords'] = list(STOPWORDS)

    def _apply_researcher_id_filter(self, value):
        self.params['researcher_id'] = str(value)
        self.filters_sql.append(' AND b.researcher_id = :researcher_id ')

    def _apply_dep_id_filter(self, value):
        pass

    def _apply_graduate_program_id_filter(self, value):
        self.params['graduate_program_id'] = str(value)
        self.filters_sql.append(
            """
            AND EXISTS (
                SELECT 1 
                FROM graduate_program_researcher gpr
                WHERE 
                    b.researcher_id = gpr.researcher_id
                    AND gpr.graduate_program_id = :graduate_program_id
            )
        """
        )

    def build_sql(self) -> str:
        filters = ' '.join(self.filters_sql)

        SCRIPT_SQL = f"""
            SELECT 
                COUNT(*) AS among,
                INITCAP(lexeme) AS term
            FROM (
                SELECT (unnest(translate(unaccent(LOWER(b.title)), '''\\.:;?(),''', ' ')::tsvector)).lexeme AS lexeme
                FROM bibliographic_production b
                WHERE 1 = 1
                {filters}
            ) sub
            WHERE
                CHAR_LENGTH(lexeme) > 3
                AND lexeme <> ALL(:stopwords)
            GROUP BY lexeme
            ORDER BY among DESC
            FETCH FIRST 20 ROWS ONLY;
        """
        return SCRIPT_SQL


class CoAuthorshipQuery(BaseQuery):
    def __init__(self, session, researcher_id):
        super().__init__(session)
        self.params['researcher_id'] = str(researcher_id)

    def build_sql(self) -> str:
        SCRIPT_SQL = """
            WITH co_authorship AS (
                SELECT r.name, i.name AS institution, COUNT(*) AS among
                FROM researcher r
                RIGHT JOIN (
                    SELECT UNNEST(ARRAY_AGG(bp.researcher_id)) AS researcher_id
                    FROM bibliographic_production bp
                    GROUP BY bp.title
                    HAVING COUNT(bp.title) > 1
                    AND :researcher_id = ANY(ARRAY_AGG(bp.researcher_id))
                ) co_authorship ON r.id = co_authorship.researcher_id
                LEFT JOIN institution i ON i.id = r.institution_id
                WHERE r.id != :researcher_id
                GROUP BY r.name, i.name

                UNION

                SELECT TRIM(UNNEST(string_to_array(opa.authors, ';'))) AS name,
                    TRIM(UNNEST(string_to_array(opa.authors_institution, ';')))
                    AS institution, COUNT(*) AS among
                FROM openalex_article opa
                INNER JOIN bibliographic_production bp
                    ON opa.article_id = bp.id
                WHERE bp.researcher_id = :researcher_id
                GROUP BY name, institution
            )
            SELECT ca.name, ca.institution, ca.among
            FROM co_authorship ca
            JOIN researcher r ON r.id = :researcher_id
            WHERE similarity(ca.name, r.name) < 0.2;
        """
        return SCRIPT_SQL


class ResearcherFilterQuery(BaseQuery):
    def build_sql(self) -> str:
        return """
            SELECT 
                (SELECT COALESCE(ARRAY_AGG(DISTINCT REPLACE(gae.name, '_', ' ')), '{}')
                 FROM great_area_expertise gae
                 INNER JOIN researcher_area_expertise r ON gae.id = r.great_area_expertise_id) as area,
                 
                (SELECT COALESCE(ARRAY_AGG(DISTINCT graduation), '{}') FROM researcher) as graduation,
                
                (SELECT COALESCE(ARRAY_AGG(DISTINCT city), '{}') FROM researcher_production WHERE city IS NOT NULL) as city,
                
                (SELECT COALESCE(ARRAY_AGG(DISTINCT i.name), '{}') 
                 FROM institution i 
                 INNER JOIN researcher r ON r.institution_id = i.id) as institution,
                 
                (SELECT COALESCE(ARRAY_AGG(DISTINCT modality_name), '{}') FROM foment) as modality,
                
                (SELECT COALESCE(ARRAY_AGG(DISTINCT gp.name), '{}') 
                 FROM graduate_program gp
                 INNER JOIN graduate_program_researcher gpr ON gpr.graduate_program_id = gp.graduate_program_id) as graduate_program,
                 
                ARRAY[]::TEXT[] as departament;
        """


class OutstandingResearchersQuery(BaseQuery):
    def __init__(self, session, limit: int = 10, pool_size: int = 100):
        super().__init__(session)
        self.params['limit'] = limit
        self.params['pool_size'] = pool_size

    def build_sql(self) -> str:
        return """
            WITH top_recent AS (
                SELECT
                    r.id, r.name, r.lattes_id, r.lattes_10_id,
                    r.abstract, r.orcid, r.graduation,
                    r.last_update AS lattes_update,
                    REPLACE(rp.great_area, '_', ' ') AS area, rp.city,
                    i.image AS image_university, i.name AS university,
                    0 AS among,
                    COALESCE(rp.articles, 0) AS articles,
                    COALESCE(rp.book_chapters, 0) AS book_chapters,
                    COALESCE(rp.book, 0) AS book,
                    COALESCE(rp.patent, 0) AS patent,
                    COALESCE(rp.software, 0) AS software,
                    COALESCE(rp.brand, 0) AS brand,
                    COALESCE(opr.h_index, 0) AS h_index,
                    COALESCE(opr.relevance_score, 0) AS relevance_score,
                    COALESCE(opr.works_count, 0) AS works_count,
                    COALESCE(opr.cited_by_count, 0) AS cited_by_count,
                    COALESCE(opr.i10_index, 0) AS i10_index,
                    opr.scopus,
                    opr.openalex,
                    r.classification, r.status, r.institution_id,
                    r.abstract_ai, r.stars
                FROM researcher r
                    LEFT JOIN institution i
                        ON i.id = r.institution_id
                    LEFT JOIN researcher_production rp
                        ON rp.researcher_id = r.id
                    LEFT JOIN openalex_researcher opr
                        ON opr.researcher_id = r.id
                WHERE
                    r.status IS True
                    AND r.last_update IS NOT NULL
                ORDER BY r.last_update DESC
                LIMIT :pool_size
            )
            SELECT * FROM top_recent
            ORDER BY RANDOM()
            LIMIT :limit;
        """
