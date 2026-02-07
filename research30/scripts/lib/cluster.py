"""Thematic clustering for research30 results.

Groups papers by research theme using OpenAlex topic names as cluster seeds,
then assigns non-OpenAlex items via MeSH terms, categories, and title keywords.
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from . import schema

# --- Constants ---

ASSIGNMENT_THRESHOLD = 0.3
MAX_CLUSTERS = 8
MIN_CLUSTER_SIZE = 2
TOPIC_SCORE_THRESHOLD = 0.5

STOP_WORDS = frozenset({
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'can', 'shall', 'not', 'no',
    'its', 'it', 'this', 'that', 'these', 'those', 'their', 'them',
    'using', 'based', 'via', 'through', 'between', 'into', 'also',
    'new', 'novel', 'study', 'analysis', 'research', 'results', 'effect',
    'effects', 'role', 'approach', 'method', 'methods', 'review',
})

ARXIV_CATEGORY_MAP = {
    'cs.AI': 'Artificial Intelligence',
    'cs.LG': 'Machine Learning',
    'cs.CL': 'Natural Language Processing',
    'cs.CV': 'Computer Vision',
    'cs.CR': 'Cryptography and Security',
    'cs.DS': 'Data Structures and Algorithms',
    'cs.IR': 'Information Retrieval',
    'cs.NE': 'Neural and Evolutionary Computing',
    'cs.RO': 'Robotics',
    'cs.SE': 'Software Engineering',
    'q-bio.BM': 'Biomolecules',
    'q-bio.CB': 'Cell Behavior',
    'q-bio.GN': 'Genomics',
    'q-bio.MN': 'Molecular Networks',
    'q-bio.NC': 'Neurons and Cognition',
    'q-bio.PE': 'Populations and Evolution',
    'q-bio.QM': 'Quantitative Methods',
    'stat.ML': 'Machine Learning',
    'stat.ME': 'Statistical Methodology',
    'physics.bio-ph': 'Biological Physics',
    'math.OC': 'Optimization and Control',
    'eess.SP': 'Signal Processing',
    'quant-ph': 'Quantum Physics',
    'cond-mat.mtrl-sci': 'Materials Science',
    'cond-mat.mes-hall': 'Mesoscale and Nanoscale Physics',
    'hep-th': 'High Energy Physics - Theory',
    'hep-ph': 'High Energy Physics - Phenomenology',
    'astro-ph': 'Astrophysics',
    'gr-qc': 'General Relativity and Quantum Cosmology',
    'math-ph': 'Mathematical Physics',
    'nucl-th': 'Nuclear Theory',
    'physics.chem-ph': 'Chemical Physics',
    'physics.comp-ph': 'Computational Physics',
    'physics.optics': 'Optics',
}


# --- Data Structure ---

@dataclass
class ThemeCluster:
    """A group of items sharing a research theme."""
    name: str
    items: list = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.items)

    @property
    def total_score(self) -> int:
        return sum(getattr(i, 'score', 0) for i in self.items)


# --- Text Utilities ---

def _tokenize(text: str) -> Set[str]:
    """Extract meaningful words: lowercase, >= 3 chars, no stop words."""
    words = re.findall(r'[a-z]{3,}', text.lower())
    return {w for w in words if w not in STOP_WORDS}


def _words_match(word_a: str, word_b: str) -> bool:
    """Check if two words match, allowing morphological variation.

    Handles cases like gene/genetic, edit/editing, engineer/engineering.
    Words match if one is a prefix of the other (min 4 shared chars).
    """
    if word_a == word_b:
        return True
    min_len = min(len(word_a), len(word_b))
    if min_len < 4:
        return False
    # Check if shorter word is a prefix of longer word
    shorter, longer = (word_a, word_b) if len(word_a) <= len(word_b) else (word_b, word_a)
    return longer.startswith(shorter)


def _count_word_matches(words_to_find: Set[str], words_to_search: Set[str]) -> int:
    """Count how many words_to_find have a match in words_to_search.

    Uses fuzzy prefix matching via _words_match.
    """
    count = 0
    for target in words_to_find:
        for candidate in words_to_search:
            if _words_match(target, candidate):
                count += 1
                break
    return count


# --- Affinity Functions ---

def _mesh_affinity(mesh_terms: List[str], cluster_name: str) -> float:
    """Compute affinity between PubMed MeSH terms and a cluster name."""
    cluster_words = _tokenize(cluster_name)
    if not cluster_words:
        return 0.0
    mesh_words = _tokenize(' '.join(mesh_terms))
    return _count_word_matches(cluster_words, mesh_words) / len(cluster_words)


def _category_affinity(category: str, cluster_name: str) -> float:
    """Compute affinity between a category name and a cluster name."""
    cat_words = _tokenize(category)
    cluster_words = _tokenize(cluster_name)
    if not cluster_words or not cat_words:
        return 0.0
    return _count_word_matches(cluster_words, cat_words) / len(cluster_words)


def _title_affinity(title: str, cluster_name: str) -> float:
    """Compute affinity between a paper title and a cluster name."""
    title_words = _tokenize(title)
    cluster_words = _tokenize(cluster_name)
    if not cluster_words:
        return 0.0
    return _count_word_matches(cluster_words, title_words) / len(cluster_words)


def compute_affinity(item, cluster_name: str) -> float:
    """Compute best-signal affinity between an item and a cluster name.

    Returns the highest affinity score from all available signals.
    """
    scores = []

    # MeSH overlap (PubMed only)
    if isinstance(item, schema.PubmedItem) and item.mesh_terms:
        scores.append(_mesh_affinity(item.mesh_terms, cluster_name) * 1.0)

    # Category mapping (arXiv)
    if isinstance(item, schema.ArxivItem) and item.primary_category:
        mapped = ARXIV_CATEGORY_MAP.get(item.primary_category, '')
        if mapped:
            scores.append(_category_affinity(mapped, cluster_name) * 0.8)

    # Category (bioRxiv/medRxiv)
    if isinstance(item, schema.BiorxivItem) and item.category:
        scores.append(_category_affinity(item.category, cluster_name) * 0.8)

    # Title keyword overlap (all items)
    title = getattr(item, 'title', '')
    if title:
        scores.append(_title_affinity(title, cluster_name) * 0.9)

    # Abstract keyword overlap (weak signal, first 200 chars)
    abstract = getattr(item, 'abstract', '')
    if abstract:
        abstract_words = _tokenize(abstract[:200])
        cluster_words = _tokenize(cluster_name)
        if cluster_words:
            matches = _count_word_matches(cluster_words, abstract_words)
            scores.append((matches / len(cluster_words)) * 0.3)

    return max(scores) if scores else 0.0


# --- Clustering Algorithm ---

def _seed_from_openalex(items: list) -> Tuple[Dict[str, list], list]:
    """Phase 1: Seed clusters from OpenAlex primary_topic_name."""
    clusters: Dict[str, list] = {}
    unassigned = []

    for item in items:
        if isinstance(item, schema.OpenAlexItem):
            name = item.primary_topic_name
            score = item.primary_topic_score
            if name and score >= TOPIC_SCORE_THRESHOLD:
                clusters.setdefault(name, []).append(item)
            else:
                unassigned.append(item)
        else:
            unassigned.append(item)

    return clusters, unassigned


def _seed_fallback(items: list) -> Dict[str, list]:
    """Create synthetic clusters when no OpenAlex topics available.

    Uses bioRxiv/arXiv categories and PubMed MeSH terms.
    """
    clusters: Dict[str, list] = {}

    for item in items:
        if isinstance(item, schema.ArxivItem) and item.primary_category:
            name = ARXIV_CATEGORY_MAP.get(item.primary_category, item.primary_category)
            clusters.setdefault(name, []).append(item)
        elif isinstance(item, schema.BiorxivItem) and item.category:
            clusters.setdefault(item.category, []).append(item)

    # If we still have nothing, try PubMed MeSH
    if not clusters:
        mesh_counter: Counter = Counter()
        for item in items:
            if isinstance(item, schema.PubmedItem) and item.mesh_terms:
                for term in item.mesh_terms[:3]:  # top 3 MeSH per article
                    mesh_counter[term] += 1
        # Use the most common MeSH terms as cluster names
        for term, count in mesh_counter.most_common(5):
            if count >= 2:
                clusters[term] = []

    return clusters


def _assign_to_clusters(clusters: Dict[str, list], unassigned: list) -> list:
    """Phase 2: Assign unassigned items to existing clusters."""
    still_unassigned = []

    for item in unassigned:
        best_cluster = None
        best_score = 0.0

        for cluster_name in clusters:
            affinity = compute_affinity(item, cluster_name)
            if affinity > best_score:
                best_score = affinity
                best_cluster = cluster_name

        if best_cluster and best_score >= ASSIGNMENT_THRESHOLD:
            clusters[best_cluster].append(item)
        else:
            still_unassigned.append(item)

    return still_unassigned


# Generic MeSH terms that match the query but don't differentiate application domains
_GENERIC_MESH = frozenset({
    'Humans', 'Animals', 'Male', 'Female',
    'Gene Editing', 'CRISPR-Cas Systems', 'CRISPR-Associated Protein 9',
    'RNA, Guide, CRISPR-Cas Systems', 'Genetic Therapy',
    'Genome Editing', 'Genome, Human',
    'Mutation', 'Base Sequence', 'DNA',
    'Cell Line', 'Cell Line, Tumor', 'Cells, Cultured',
    'Gene Expression', 'Gene Expression Regulation',
    'Molecular Sequence Data',
})


def _subcluster_overflow(overflow: list, existing_names: Set[str]) -> Tuple[Dict[str, list], list]:
    """Create sub-clusters from overflow items using MeSH terms and categories.

    When primary clustering leaves too many items unassigned, this finds
    application-domain sub-themes using differentiating MeSH terms.
    """
    # Collect differentiating MeSH terms (exclude generic ones)
    mesh_counter: Counter = Counter()
    for item in overflow:
        if isinstance(item, schema.PubmedItem) and item.mesh_terms:
            for term in item.mesh_terms[:5]:
                if term not in _GENERIC_MESH:
                    mesh_counter[term] += 1

    # Also count bioRxiv/arXiv categories
    cat_counter: Counter = Counter()
    for item in overflow:
        if isinstance(item, schema.ArxivItem) and item.primary_category:
            name = ARXIV_CATEGORY_MAP.get(item.primary_category, item.primary_category)
            cat_counter[name] += 1
        elif isinstance(item, schema.BiorxivItem) and item.category:
            cat_counter[item.category] += 1

    # Build candidate sub-cluster names from most common terms
    candidates: Dict[str, list] = {}
    for term, count in mesh_counter.most_common(10):
        if count >= MIN_CLUSTER_SIZE and term not in existing_names:
            candidates[term] = []
    for cat, count in cat_counter.most_common(5):
        if count >= MIN_CLUSTER_SIZE and cat not in existing_names and cat not in candidates:
            candidates[cat] = []

    if not candidates:
        return {}, overflow

    # Assign overflow items to sub-clusters
    still_unassigned = _assign_to_clusters(candidates, overflow)
    return candidates, still_unassigned


def _name_similarity(name_a: str, name_b: str) -> float:
    """Compute word overlap between two cluster names."""
    words_a = _tokenize(name_a)
    words_b = _tokenize(name_b)
    if not words_a or not words_b:
        return 0.0
    shared = len(words_a & words_b)
    return shared / min(len(words_a), len(words_b))


def _consolidate(clusters: Dict[str, list], unassigned: list) -> List[ThemeCluster]:
    """Phase 3: Merge small clusters, cap total, build final list."""
    # Merge clusters smaller than MIN_CLUSTER_SIZE
    small = [name for name, items in clusters.items() if len(items) < MIN_CLUSTER_SIZE]
    for name in small:
        items = clusters.pop(name)
        # Try to merge into most similar larger cluster
        best_target = None
        best_sim = 0.0
        for other_name in clusters:
            if len(clusters[other_name]) >= MIN_CLUSTER_SIZE:
                sim = _name_similarity(name, other_name)
                if sim > best_sim:
                    best_sim = sim
                    best_target = other_name
        if best_target and best_sim > 0:
            clusters[best_target].extend(items)
        else:
            unassigned.extend(items)

    # Cap at MAX_CLUSTERS; merge smallest into "Other"
    if len(clusters) > MAX_CLUSTERS:
        sorted_clusters = sorted(clusters.items(), key=lambda kv: -sum(i.score for i in kv[1]))
        keep = dict(sorted_clusters[:MAX_CLUSTERS])
        for name, items in sorted_clusters[MAX_CLUSTERS:]:
            unassigned.extend(items)
        clusters = keep

    # Build final cluster list
    result = []
    for name, items in clusters.items():
        items.sort(key=lambda i: (-i.score, getattr(i, 'date', '') or ''), reverse=False)
        # Re-sort: highest score first, then most recent date
        items.sort(key=lambda i: (-i.score,))
        result.append(ThemeCluster(name=name, items=items))

    # Sort clusters by total score descending
    result.sort(key=lambda c: -c.total_score)

    # Add "Other" bucket if there are unassigned items
    if unassigned:
        unassigned.sort(key=lambda i: (-i.score,))
        result.append(ThemeCluster(name="Other", items=unassigned))

    return result


def cluster_by_theme(
    all_items: list,
    fallback_name: str = "Research Results",
) -> List[ThemeCluster]:
    """Group items by research theme.

    Uses OpenAlex primary_topic_name as cluster seeds, then assigns
    remaining items via MeSH terms, categories, and title keywords.

    Args:
        all_items: Flat list of all deduped items (mixed types).
        fallback_name: Name for single-cluster fallback when no topics found.

    Returns:
        List of ThemeCluster, sorted by total score descending.
    """
    if not all_items:
        return []

    # Phase 1: Seed clusters from OpenAlex topics
    clusters, unassigned = _seed_from_openalex(all_items)

    # If no OpenAlex clusters, try fallback seeding
    if not clusters:
        clusters = _seed_fallback(all_items)
        # All items are unassigned relative to these new clusters
        unassigned = all_items
        # Remove items that were already placed in fallback clusters
        placed = set()
        for items in clusters.values():
            for item in items:
                placed.add(id(item))
        unassigned = [i for i in unassigned if id(i) not in placed]

    # If still no clusters, put everything in one bucket
    if not clusters:
        all_items_sorted = sorted(all_items, key=lambda i: (-i.score,))
        return [ThemeCluster(name=fallback_name, items=all_items_sorted)]

    # Phase 2: Assign unassigned items to clusters
    still_unassigned = _assign_to_clusters(clusters, unassigned)

    # Phase 2.5: Sub-cluster overflow when too many items unassigned
    total = len(all_items)
    if still_unassigned and len(still_unassigned) > total * 0.4:
        sub_clusters, still_unassigned = _subcluster_overflow(
            still_unassigned, set(clusters.keys())
        )
        clusters.update(sub_clusters)

    # Phase 3: Consolidate
    return _consolidate(clusters, still_unassigned)
