"""Data schemas for research30 skill."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AcademicEngagement:
    """Academic engagement metrics."""
    published_doi: Optional[str] = None
    published_journal: Optional[str] = None
    citation_count: Optional[int] = None
    downloads: Optional[int] = None
    likes: Optional[int] = None
    author_count: Optional[int] = None

    def to_dict(self) -> Optional[Dict[str, Any]]:
        d = {}
        if self.published_doi is not None:
            d['published_doi'] = self.published_doi
        if self.published_journal is not None:
            d['published_journal'] = self.published_journal
        if self.citation_count is not None:
            d['citation_count'] = self.citation_count
        if self.downloads is not None:
            d['downloads'] = self.downloads
        if self.likes is not None:
            d['likes'] = self.likes
        if self.author_count is not None:
            d['author_count'] = self.author_count
        return d if d else None


@dataclass
class SubScores:
    """Component scores."""
    relevance: int = 0
    recency: int = 0
    engagement: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            'relevance': self.relevance,
            'recency': self.recency,
            'engagement': self.engagement,
        }


@dataclass
class BiorxivItem:
    """Normalized bioRxiv/medRxiv item."""
    id: str
    preprint_doi: str
    title: str
    authors: str
    abstract: str
    category: str
    source: str  # "biorxiv" or "medrxiv"
    url: str
    date: Optional[str] = None
    date_confidence: str = "low"
    engagement: Optional[AcademicEngagement] = None
    relevance: float = 0.0
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'preprint_doi': self.preprint_doi,
            'title': self.title,
            'authors': self.authors,
            'abstract': self.abstract,
            'category': self.category,
            'source': self.source,
            'url': self.url,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'engagement': self.engagement.to_dict() if self.engagement else None,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
        }


@dataclass
class ArxivItem:
    """Normalized arXiv item."""
    id: str
    arxiv_id: str
    title: str
    authors: str
    abstract: str
    primary_category: str
    categories: List[str]
    url: str
    date: Optional[str] = None
    date_confidence: str = "low"
    engagement: Optional[AcademicEngagement] = None
    relevance: float = 0.0
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'arxiv_id': self.arxiv_id,
            'title': self.title,
            'authors': self.authors,
            'abstract': self.abstract,
            'primary_category': self.primary_category,
            'categories': self.categories,
            'url': self.url,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'engagement': self.engagement.to_dict() if self.engagement else None,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
        }


@dataclass
class PubmedItem:
    """Normalized PubMed item."""
    id: str
    pmid: str
    title: str
    authors: str
    abstract: str
    journal: str
    doi: Optional[str]
    url: str
    date: Optional[str] = None
    date_confidence: str = "low"
    engagement: Optional[AcademicEngagement] = None
    relevance: float = 0.0
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'pmid': self.pmid,
            'title': self.title,
            'authors': self.authors,
            'abstract': self.abstract,
            'journal': self.journal,
            'doi': self.doi,
            'url': self.url,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'engagement': self.engagement.to_dict() if self.engagement else None,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
        }


@dataclass
class HuggingFaceItem:
    """Normalized HuggingFace item."""
    id: str
    hf_id: str
    title: str
    author: str
    item_type: str  # "model", "dataset", or "paper"
    tags: List[str]
    url: str
    date: Optional[str] = None
    date_confidence: str = "low"
    engagement: Optional[AcademicEngagement] = None
    relevance: float = 0.0
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'hf_id': self.hf_id,
            'title': self.title,
            'author': self.author,
            'item_type': self.item_type,
            'tags': self.tags,
            'url': self.url,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'engagement': self.engagement.to_dict() if self.engagement else None,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
        }


@dataclass
class OpenAlexItem:
    """Normalized OpenAlex item."""
    id: str
    openalex_id: str
    title: str
    authors: str
    abstract: str
    doi: Optional[str]
    source_name: str  # journal/repo name e.g. "Nature", "bioRxiv"
    source_type: str  # "journal", "repository", etc.
    work_type: str    # "article", "preprint", etc.
    url: str
    date: Optional[str] = None
    date_confidence: str = "low"
    engagement: Optional[AcademicEngagement] = None
    relevance: float = 0.0
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'openalex_id': self.openalex_id,
            'title': self.title,
            'authors': self.authors,
            'abstract': self.abstract,
            'doi': self.doi,
            'source_name': self.source_name,
            'source_type': self.source_type,
            'work_type': self.work_type,
            'url': self.url,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'engagement': self.engagement.to_dict() if self.engagement else None,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
        }


@dataclass
class Report:
    """Full research report."""
    topic: str
    range_from: str
    range_to: str
    generated_at: str
    mode: str
    biorxiv: List[BiorxivItem] = field(default_factory=list)
    medrxiv: List[BiorxivItem] = field(default_factory=list)
    arxiv: List[ArxivItem] = field(default_factory=list)
    pubmed: List[PubmedItem] = field(default_factory=list)
    huggingface: List[HuggingFaceItem] = field(default_factory=list)
    openalex: List[OpenAlexItem] = field(default_factory=list)
    biorxiv_error: Optional[str] = None
    medrxiv_error: Optional[str] = None
    arxiv_error: Optional[str] = None
    pubmed_error: Optional[str] = None
    huggingface_error: Optional[str] = None
    openalex_error: Optional[str] = None
    from_cache: bool = False
    cache_age_hours: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            'topic': self.topic,
            'range': {
                'from': self.range_from,
                'to': self.range_to,
            },
            'generated_at': self.generated_at,
            'mode': self.mode,
            'biorxiv': [i.to_dict() for i in self.biorxiv],
            'medrxiv': [i.to_dict() for i in self.medrxiv],
            'arxiv': [i.to_dict() for i in self.arxiv],
            'pubmed': [i.to_dict() for i in self.pubmed],
            'huggingface': [i.to_dict() for i in self.huggingface],
            'openalex': [i.to_dict() for i in self.openalex],
        }
        for src in ('biorxiv', 'medrxiv', 'arxiv', 'pubmed', 'huggingface', 'openalex'):
            err = getattr(self, f'{src}_error')
            if err:
                d[f'{src}_error'] = err
        if self.from_cache:
            d['from_cache'] = self.from_cache
        if self.cache_age_hours is not None:
            d['cache_age_hours'] = self.cache_age_hours
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Report":
        """Create Report from serialized dict."""
        range_data = data.get('range', {})
        range_from = range_data.get('from', data.get('range_from', ''))
        range_to = range_data.get('to', data.get('range_to', ''))

        def _parse_engagement(raw: Optional[dict]) -> Optional[AcademicEngagement]:
            if not raw:
                return None
            return AcademicEngagement(**raw)

        def _parse_subs(raw: Optional[dict]) -> SubScores:
            if not raw:
                return SubScores()
            return SubScores(**raw)

        biorxiv_items = []
        for r in data.get('biorxiv', []):
            biorxiv_items.append(BiorxivItem(
                id=r['id'], preprint_doi=r['preprint_doi'], title=r['title'],
                authors=r['authors'], abstract=r['abstract'], category=r['category'],
                source=r['source'], url=r['url'], date=r.get('date'),
                date_confidence=r.get('date_confidence', 'low'),
                engagement=_parse_engagement(r.get('engagement')),
                relevance=r.get('relevance', 0.0), why_relevant=r.get('why_relevant', ''),
                subs=_parse_subs(r.get('subs')), score=r.get('score', 0),
            ))

        medrxiv_items = []
        for r in data.get('medrxiv', []):
            medrxiv_items.append(BiorxivItem(
                id=r['id'], preprint_doi=r['preprint_doi'], title=r['title'],
                authors=r['authors'], abstract=r['abstract'], category=r['category'],
                source=r['source'], url=r['url'], date=r.get('date'),
                date_confidence=r.get('date_confidence', 'low'),
                engagement=_parse_engagement(r.get('engagement')),
                relevance=r.get('relevance', 0.0), why_relevant=r.get('why_relevant', ''),
                subs=_parse_subs(r.get('subs')), score=r.get('score', 0),
            ))

        arxiv_items = []
        for r in data.get('arxiv', []):
            arxiv_items.append(ArxivItem(
                id=r['id'], arxiv_id=r['arxiv_id'], title=r['title'],
                authors=r['authors'], abstract=r['abstract'],
                primary_category=r['primary_category'], categories=r.get('categories', []),
                url=r['url'], date=r.get('date'),
                date_confidence=r.get('date_confidence', 'low'),
                engagement=_parse_engagement(r.get('engagement')),
                relevance=r.get('relevance', 0.0), why_relevant=r.get('why_relevant', ''),
                subs=_parse_subs(r.get('subs')), score=r.get('score', 0),
            ))

        pubmed_items = []
        for r in data.get('pubmed', []):
            pubmed_items.append(PubmedItem(
                id=r['id'], pmid=r['pmid'], title=r['title'],
                authors=r['authors'], abstract=r['abstract'],
                journal=r['journal'], doi=r.get('doi'),
                url=r['url'], date=r.get('date'),
                date_confidence=r.get('date_confidence', 'low'),
                engagement=_parse_engagement(r.get('engagement')),
                relevance=r.get('relevance', 0.0), why_relevant=r.get('why_relevant', ''),
                subs=_parse_subs(r.get('subs')), score=r.get('score', 0),
            ))

        hf_items = []
        for r in data.get('huggingface', []):
            hf_items.append(HuggingFaceItem(
                id=r['id'], hf_id=r['hf_id'], title=r['title'],
                author=r['author'], item_type=r['item_type'],
                tags=r.get('tags', []),
                url=r['url'], date=r.get('date'),
                date_confidence=r.get('date_confidence', 'low'),
                engagement=_parse_engagement(r.get('engagement')),
                relevance=r.get('relevance', 0.0), why_relevant=r.get('why_relevant', ''),
                subs=_parse_subs(r.get('subs')), score=r.get('score', 0),
            ))

        openalex_items = []
        for r in data.get('openalex', []):
            openalex_items.append(OpenAlexItem(
                id=r['id'], openalex_id=r['openalex_id'], title=r['title'],
                authors=r['authors'], abstract=r['abstract'],
                doi=r.get('doi'), source_name=r.get('source_name', ''),
                source_type=r.get('source_type', ''), work_type=r.get('work_type', ''),
                url=r['url'], date=r.get('date'),
                date_confidence=r.get('date_confidence', 'low'),
                engagement=_parse_engagement(r.get('engagement')),
                relevance=r.get('relevance', 0.0), why_relevant=r.get('why_relevant', ''),
                subs=_parse_subs(r.get('subs')), score=r.get('score', 0),
            ))

        return cls(
            topic=data['topic'], range_from=range_from, range_to=range_to,
            generated_at=data['generated_at'], mode=data['mode'],
            biorxiv=biorxiv_items, medrxiv=medrxiv_items,
            arxiv=arxiv_items, pubmed=pubmed_items, huggingface=hf_items,
            openalex=openalex_items,
            biorxiv_error=data.get('biorxiv_error'),
            medrxiv_error=data.get('medrxiv_error'),
            arxiv_error=data.get('arxiv_error'),
            pubmed_error=data.get('pubmed_error'),
            huggingface_error=data.get('huggingface_error'),
            openalex_error=data.get('openalex_error'),
            from_cache=data.get('from_cache', False),
            cache_age_hours=data.get('cache_age_hours'),
        )


def create_report(topic: str, from_date: str, to_date: str, mode: str) -> Report:
    """Create a new report with metadata."""
    return Report(
        topic=topic,
        range_from=from_date,
        range_to=to_date,
        generated_at=datetime.now(timezone.utc).isoformat(),
        mode=mode,
    )
