import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.institution import PeriodicalMagazine
from simcc.core.db.models.production import (
    BibliographicProduction,
    BibliographicProductionArticle,
    BibliographicProductionBook,
    BibliographicProductionBookChapter,
)
from tests.factories.production import next_sequence_code


@pytest.mark.asyncio
async def test_cannot_create_duplicate_article_for_same_production(
    session: AsyncSession, researcher_factory
):
    researcher = await researcher_factory()

    production = BibliographicProduction(
        researcher_id=researcher.id,
        sequence_code=next_sequence_code(),
        title='Artigo de Teste',
        type='ARTICLE',
        year='2024',
        year_=2024,
    )
    session.add(production)
    await session.flush()

    magazine = PeriodicalMagazine(name='Revista Unicidade')
    session.add(magazine)
    await session.flush()

    article1 = BibliographicProductionArticle(
        bibliographic_production_id=production.id,
        periodical_magazine_id=magazine.id,
        periodical_magazine_name='Revista Unicidade',
        qualis='A1',
    )
    session.add(article1)
    await session.commit()

    article2 = BibliographicProductionArticle(
        bibliographic_production_id=production.id,
        periodical_magazine_id=magazine.id,
        periodical_magazine_name='Revista Unicidade Duplicada',
        qualis='A2',
    )
    session.add(article2)

    with pytest.raises(IntegrityError):
        await session.commit()

    await session.rollback()


@pytest.mark.asyncio
async def test_cannot_create_duplicate_book_for_same_production(
    session: AsyncSession, researcher_factory
):
    researcher = await researcher_factory()

    production = BibliographicProduction(
        researcher_id=researcher.id,
        sequence_code=next_sequence_code(),
        title='Livro de Teste',
        type='BOOK',
        year='2024',
        year_=2024,
    )
    session.add(production)
    await session.flush()

    book1 = BibliographicProductionBook(
        bibliographic_production_id=production.id,
        isbn='978-85-1234-567-8',
        publishing_company='Editora A',
    )
    session.add(book1)
    await session.commit()

    book2 = BibliographicProductionBook(
        bibliographic_production_id=production.id,
        isbn='978-85-9876-543-2',
        publishing_company='Editora B',
    )
    session.add(book2)

    with pytest.raises(IntegrityError):
        await session.commit()

    await session.rollback()


@pytest.mark.asyncio
async def test_cannot_create_duplicate_book_chapter_for_same_production(
    session: AsyncSession, researcher_factory
):
    researcher = await researcher_factory()

    production = BibliographicProduction(
        researcher_id=researcher.id,
        sequence_code=next_sequence_code(),
        title='Capítulo de Teste',
        type='BOOK_CHAPTER',
        year='2024',
        year_=2024,
    )
    session.add(production)
    await session.flush()

    chapter1 = BibliographicProductionBookChapter(
        bibliographic_production_id=production.id,
        book_title='Livro Coletânea 1',
        publishing_company='Editora A',
    )
    session.add(chapter1)
    await session.commit()

    chapter2 = BibliographicProductionBookChapter(
        bibliographic_production_id=production.id,
        book_title='Livro Coletânea 2',
        publishing_company='Editora B',
    )
    session.add(chapter2)

    with pytest.raises(IntegrityError):
        await session.commit()

    await session.rollback()


@pytest.mark.asyncio
async def test_valid_1_to_1_bibliographic_production_children(
    session: AsyncSession, researcher_factory
):
    researcher = await researcher_factory()

    # Artigo
    prod_article = BibliographicProduction(
        researcher_id=researcher.id,
        sequence_code=next_sequence_code(),
        title='Artigo 1:1',
        type='ARTICLE',
        year='2024',
        year_=2024,
    )
    session.add(prod_article)
    magazine = PeriodicalMagazine(name='Revista 1:1')
    session.add(magazine)
    await session.flush()

    article = BibliographicProductionArticle(
        bibliographic_production_id=prod_article.id,
        periodical_magazine_id=magazine.id,
        periodical_magazine_name='Revista 1:1',
        qualis='A1',
    )
    session.add(article)

    # Livro
    prod_book = BibliographicProduction(
        researcher_id=researcher.id,
        sequence_code=next_sequence_code(),
        title='Livro 1:1',
        type='BOOK',
        year='2024',
        year_=2024,
    )
    session.add(prod_book)
    await session.flush()

    book = BibliographicProductionBook(
        bibliographic_production_id=prod_book.id,
        isbn='978-00-0000-000-0',
        publishing_company='Editora C',
    )
    session.add(book)

    # Capítulo
    prod_chp = BibliographicProduction(
        researcher_id=researcher.id,
        sequence_code=next_sequence_code(),
        title='Capítulo 1:1',
        type='BOOK_CHAPTER',
        year='2024',
        year_=2024,
    )
    session.add(prod_chp)
    await session.flush()

    chp = BibliographicProductionBookChapter(
        bibliographic_production_id=prod_chp.id,
        book_title='Coletânea 1:1',
        publishing_company='Editora D',
    )
    session.add(chp)

    await session.commit()

    assert article.id is not None
    assert book.id is not None
    assert chp.id is not None
