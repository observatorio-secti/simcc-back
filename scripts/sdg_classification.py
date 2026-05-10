import json

import pandas as pd
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from simcc.config import Settings
from simcc.repositories import conn

SETTINGS = Settings()

BATCH_SIZE = 20

ods = {
    '1': {
        'title': '1 - Erradicação da pobreza',
        'description': 'Erradicação da pobreza em todas as formas e lugares. Foca na implementação de sistemas de proteção social e na garantia de direitos iguais ao acesso a recursos econômicos e serviços básicos.',
    },
    '2': {
        'title': '2 - Fome zero e agricultura sustentável',
        'description': 'Erradicação da fome e alcance da segurança alimentar. Promove práticas agrícolas que aumentem a produtividade e garantam a manutenção de ecossistemas.',
    },
    '3': {
        'title': '3 - Saúde e bem-estar',
        'description': 'Asseguração de uma vida saudável e promoção do bem-estar para todas as idades. Inclui a redução da mortalidade materna e infantil, além do combate a doenças transmissíveis e não transmissíveis.',
    },
    '4': {
        'title': '4 - Educação de qualidade',
        'description': 'Garantia de educação inclusiva, equitativa e de qualidade. Foca na promoção de oportunidades de aprendizagem ao longo da vida e no desenvolvimento de competências técnicas e profissionais.',
    },
    '5': {
        'title': '5 - Igualdade de gênero',
        'description': 'Alcance da igualdade de gênero e empoderamento de mulheres e meninas. Visa a eliminação de todas as formas de discriminação e violência nas esferas pública e privada.',
    },
    '6': {
        'title': '6 - Água potável e saneamento',
        'description': 'Asseguração da disponibilidade e gestão sustentável da água e saneamento. Aborda a melhoria da qualidade da água, redução da poluição e aumento da eficiência no uso dos recursos hídricos.',
    },
    '7': {
        'title': '7 - Energia limpa e acessível',
        'description': 'Acesso a fontes de energia modernas, confiáveis e preços acessíveis. Incentiva o aumento da participação de energias renováveis na matriz energética global e a expansão da infraestrutura tecnológica.',
    },
    '8': {
        'title': '8 - Trabalho decente e crescimento econômico',
        'description': 'Promoção do crescimento econômico sustentado, inclusive e sustentável. Foca no alcance do emprego pleno e produtivo e na proteção dos direitos trabalhistas e ambientes de trabalho seguros.',
    },
    '9': {
        'title': '9 - Indústria, inovação e infraestrutura',
        'description': 'Construção de infraestruturas resilientes e fomento à inovação. Promove a industrialização inclusiva e o aumento do investimento em pesquisa científica e capacidade tecnológica industrial.',
    },
    '10': {
        'title': '10 - Redução das desigualdades',
        'description': 'Redução da desigualdade dentro dos países e entre eles. Implementa políticas fiscais, salariais e de proteção social para atingir progressivamente a inclusão de grupos vulneráveis.',
    },
    '11': {
        'title': '11 - Cidades e comunidades sustentáveis',
        'description': 'Transformação dos assentamentos humanos em locais inclusivos, seguros e resilientes. Inclui o acesso à habitação segura, serviços básicos e sistemas de transporte público urbanos.',
    },
    '12': {
        'title': '12 - Consumo e produção responsáveis',
        'description': 'Asseguração de padrões de produção e de consumo sustentáveis. Foca na gestão eficiente de recursos naturais, redução da geração de resíduos e manejo de produtos químicos.',
    },
    '13': {
        'title': '13 - Ação contra a mudança global do clima',
        'description': 'Adoção de medidas urgentes para combater as mudanças climáticas e seus impactos. Envolve o fortalecimento da resiliência a desastres naturais e a integração de estratégias em políticas nacionais.',
    },
    '14': {
        'title': '14 - Vida na água',
        'description': 'Conservação e uso sustentável dos oceanos, mares e recursos marinhos. Visa a prevenção da poluição marinha e a regulamentação da exploração de estoques pesqueiros para restauração de ecossistemas.',
    },
    '15': {
        'title': '15 - Vida terrestre',
        'description': 'Proteção e restauração dos ecossistemas terrestres. Combate a desertificação, detém a degradação da terra e a perda de biodiversidade através da gestão sustentável de florestas.',
    },
    '16': {
        'title': '16 - Paz, justiça e instituições eficazes',
        'description': 'Promoção de sociedades pacíficas e acesso à justiça para todos. Foca na redução de todas as formas de violência e na construção de instituições eficazes, responsáveis e transparentes.',
    },
    '17': {
        'title': '17 - Parcerias e meios de implementação',
        'description': 'Fortalecimento dos meios de implementação e revitalização da parceria global. Envolve mobilização de recursos financeiros, compartilhamento de tecnologia e capacitação entre as nações.',
    },
}

ods_text = '\n\n'.join([
    f'ODS {key}:\nTítulo: {value["title"]}\nDescrição: {value["description"]}'
    for key, value in ods.items()
])

BASE_SQL = """
SELECT bp.id, bp.researcher_id, bp.title
FROM bibliographic_production bp
LEFT JOIN sdg_alignment ao
    ON ao.reference_id = bp.id
    AND ao.type = 'ARTICLE'
WHERE bp.type = 'ARTICLE'
AND bp.year::INT > 2017
AND ao.reference_id IS NULL
ORDER BY bp.id
LIMIT {limit} OFFSET {offset}
"""

MODEL = 'gpt-5.4-nano'

llm = ChatOpenAI(
    model=MODEL,
    temperature=0,
    api_key=SETTINGS.OPENAI_API_KEY,
)

prompt = ChatPromptTemplate.from_messages([
    (
        'system',
        """
Você classifica artigos científicos de acordo com os Objetivos de Desenvolvimento Sustentável (ODS).

Analise o título do artigo e retorne as 3 ODS com maior aderência.

A resposta deve ser SOMENTE um JSON válido no formato:
{{
  "sdgs": ["1", "3", "9"]
}}
""",
    ),
    (
        'human',
        """
ODS disponíveis:
{ods}

Título do artigo:
{title}
""",
    ),
])

chain = prompt | llm | StrOutputParser()

offset = 0
all_results = []

while True:
    SQL = BASE_SQL.format(limit=BATCH_SIZE, offset=offset)
    result = conn.select(SQL)
    articles = pd.DataFrame(result)

    if articles.empty:
        break

    inputs = [
        {
            'title': row['title'],
            'ods': ods_text,
        }
        for _, row in articles.iterrows()
    ]

    outputs = chain.batch(inputs, {'max_concurrency': 5})

    parsed_outputs = []

    for output in outputs:
        try:
            data = json.loads(output)
            sdgs = data.get('sdgs', [])

            sdgs = [
                str(sdg).strip() for sdg in sdgs if str(sdg).strip().isdigit()
            ][:3]

        except Exception:
            sdgs = []

        parsed_outputs.append(sdgs)

    articles['ods_preditos'] = parsed_outputs

    all_results.append(articles)

    for _, row in articles.iterrows():
        reference_id = row['id']
        sdg_ids = row['ods_preditos']

        for sdg_id in sdg_ids:
            sql = f"""
            INSERT INTO sdg_alignment (reference_id, type, sdg_id)
            SELECT
                '{reference_id}',
                'ARTICLE',
                (
                    SELECT id
                    FROM public.sdg
                    WHERE number = {sdg_id}
                )
            WHERE NOT EXISTS (
                SELECT 1
                FROM sdg_alignment
                WHERE reference_id = '{reference_id}'
                AND type = 'ARTICLE'
                AND sdg_id = (
                    SELECT id
                    FROM public.sdg
                    WHERE number = {sdg_id}
                )
            );
            """

            conn.exec(sql)

    offset += BATCH_SIZE

final_df = (
    pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()
)

final_df.to_csv('resultado.csv', index=False)

print(final_df)
