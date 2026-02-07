"""XML parsing helpers for arXiv Atom and PubMed XML."""

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional


# arXiv Atom namespace
ATOM_NS = '{http://www.w3.org/2005/Atom}'
ARXIV_NS = '{http://arxiv.org/schemas/atom}'


def parse_arxiv_atom(xml_text: str) -> List[Dict[str, Any]]:
    """Parse arXiv Atom XML feed into list of paper dicts.

    Returns list of dicts with keys:
        arxiv_id, title, authors, abstract, published, updated,
        primary_category, categories, link
    """
    results = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return results

    for entry in root.findall(f'{ATOM_NS}entry'):
        # Extract arxiv_id from <id> tag
        id_elem = entry.find(f'{ATOM_NS}id')
        arxiv_url = id_elem.text.strip() if id_elem is not None and id_elem.text else ''
        arxiv_id = arxiv_url.split('/abs/')[-1] if '/abs/' in arxiv_url else arxiv_url

        # Title
        title_elem = entry.find(f'{ATOM_NS}title')
        title = title_elem.text.strip().replace('\n', ' ') if title_elem is not None and title_elem.text else ''

        # Authors
        authors = []
        for author_elem in entry.findall(f'{ATOM_NS}author'):
            name_elem = author_elem.find(f'{ATOM_NS}name')
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text.strip())

        # Abstract/summary
        summary_elem = entry.find(f'{ATOM_NS}summary')
        abstract = summary_elem.text.strip().replace('\n', ' ') if summary_elem is not None and summary_elem.text else ''

        # Published date
        pub_elem = entry.find(f'{ATOM_NS}published')
        published = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ''

        # Updated date
        upd_elem = entry.find(f'{ATOM_NS}updated')
        updated = upd_elem.text.strip() if upd_elem is not None and upd_elem.text else ''

        # Primary category
        prim_cat_elem = entry.find(f'{ARXIV_NS}primary_category')
        primary_category = prim_cat_elem.get('term', '') if prim_cat_elem is not None else ''

        # All categories
        categories = []
        for cat_elem in entry.findall(f'{ATOM_NS}category'):
            term = cat_elem.get('term', '')
            if term:
                categories.append(term)

        # Link to abstract page
        link = arxiv_url
        for link_elem in entry.findall(f'{ATOM_NS}link'):
            if link_elem.get('type') == 'text/html':
                link = link_elem.get('href', arxiv_url)
                break

        results.append({
            'arxiv_id': arxiv_id,
            'title': title,
            'authors': ', '.join(authors),
            'author_count': len(authors),
            'abstract': abstract,
            'published': published,
            'updated': updated,
            'primary_category': primary_category,
            'categories': categories,
            'link': link,
        })

    return results


def parse_pubmed_esearch(json_data: dict) -> List[str]:
    """Extract PMIDs from PubMed ESearch JSON response."""
    result = json_data.get('esearchresult', {})
    return result.get('idlist', [])


def parse_pubmed_efetch(xml_text: str) -> List[Dict[str, Any]]:
    """Parse PubMed EFetch XML into list of article dicts.

    Returns list of dicts with keys:
        pmid, title, authors, abstract, journal, doi, pub_date
    """
    results = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return results

    for article in root.findall('.//PubmedArticle'):
        medline = article.find('MedlineCitation')
        if medline is None:
            continue

        # PMID
        pmid_elem = medline.find('PMID')
        pmid = pmid_elem.text.strip() if pmid_elem is not None and pmid_elem.text else ''

        # Article data
        art = medline.find('Article')
        if art is None:
            continue

        # Title
        title_elem = art.find('ArticleTitle')
        title = _extract_text(title_elem)

        # Abstract
        abstract_parts = []
        abstract_elem = art.find('Abstract')
        if abstract_elem is not None:
            for text_elem in abstract_elem.findall('AbstractText'):
                label = text_elem.get('Label', '')
                text = _extract_text(text_elem)
                if label and text:
                    abstract_parts.append(f"{label}: {text}")
                elif text:
                    abstract_parts.append(text)
        abstract = ' '.join(abstract_parts)

        # Authors
        authors = []
        author_list = art.find('AuthorList')
        if author_list is not None:
            for author_elem in author_list.findall('Author'):
                last = author_elem.find('LastName')
                first = author_elem.find('ForeName')
                if last is not None and last.text:
                    name = last.text
                    if first is not None and first.text:
                        name = f"{last.text} {first.text[0]}"
                    authors.append(name)

        # Journal
        journal_elem = art.find('Journal/Title')
        journal = journal_elem.text.strip() if journal_elem is not None and journal_elem.text else ''

        # DOI
        doi = ''
        article_id_list = article.find('PubmedData/ArticleIdList')
        if article_id_list is not None:
            for aid in article_id_list.findall('ArticleId'):
                if aid.get('IdType') == 'doi' and aid.text:
                    doi = aid.text.strip()
                    break

        # Publication date
        pub_date = _extract_pub_date(art)

        # Citation count (not available in efetch, set to None)
        results.append({
            'pmid': pmid,
            'title': title,
            'authors': ', '.join(authors),
            'author_count': len(authors),
            'abstract': abstract,
            'journal': journal,
            'doi': doi,
            'pub_date': pub_date,
        })

    return results


def _extract_text(elem) -> str:
    """Extract all text content from an element, including mixed content."""
    if elem is None:
        return ''
    # itertext() gets text from element and all children
    return ''.join(elem.itertext()).strip()


def _extract_pub_date(article_elem) -> Optional[str]:
    """Extract publication date from Article element."""
    # Try ArticleDate first (electronic publication date)
    for date_elem in article_elem.findall('ArticleDate'):
        year = date_elem.find('Year')
        month = date_elem.find('Month')
        day = date_elem.find('Day')
        if year is not None and year.text:
            y = year.text
            m = month.text.zfill(2) if month is not None and month.text else '01'
            d = day.text.zfill(2) if day is not None and day.text else '01'
            return f"{y}-{m}-{d}"

    # Fall back to Journal PubDate
    pub_date = article_elem.find('Journal/JournalIssue/PubDate')
    if pub_date is not None:
        year = pub_date.find('Year')
        month = pub_date.find('Month')
        day = pub_date.find('Day')
        if year is not None and year.text:
            y = year.text
            m = _month_to_num(month.text) if month is not None and month.text else '01'
            d = day.text.zfill(2) if day is not None and day.text else '01'
            return f"{y}-{m}-{d}"

    return None


def _month_to_num(month_str: str) -> str:
    """Convert month name/abbreviation to zero-padded number."""
    months = {
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
    }
    # Try numeric first
    try:
        n = int(month_str)
        return str(n).zfill(2)
    except ValueError:
        pass
    return months.get(month_str.lower()[:3], '01')
