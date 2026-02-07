"""Tests for huggingface module."""

import json
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent.resolve()
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from lib import huggingface

FIXTURES_DIR = TESTS_DIR.parent / "fixtures"


def load_models():
    with open(FIXTURES_DIR / "hf_models_sample.json") as f:
        return json.load(f)


def load_papers():
    with open(FIXTURES_DIR / "hf_papers_sample.json") as f:
        return json.load(f)


def test_search_huggingface_mock():
    """Test HuggingFace search with mock data."""
    models = load_models()
    papers = load_papers()
    items, error = huggingface.search_huggingface(
        topic="CRISPR gene editing",
        from_date="2025-01-01",
        to_date="2025-01-31",
        depth="default",
        mock_models=models,
        mock_papers=papers,
    )
    # Should find at least some matching items
    assert len(items) >= 1


def test_huggingface_item_fields():
    """Test that items have required fields."""
    models = load_models()
    papers = load_papers()
    items, _ = huggingface.search_huggingface(
        topic="CRISPR",
        from_date="2025-01-01",
        to_date="2025-01-31",
        mock_models=models,
        mock_papers=papers,
    )
    for item in items:
        assert 'hf_id' in item
        assert 'title' in item
        assert 'item_type' in item
        assert item['item_type'] in ('model', 'dataset', 'paper')
        assert 'url' in item
        assert 'relevance' in item


def test_huggingface_model_types():
    """Test that models have correct item_type."""
    models = load_models()
    items, _ = huggingface.search_huggingface(
        topic="CRISPR",
        from_date="2025-01-01",
        to_date="2025-01-31",
        mock_models=models,
        mock_papers=[],
    )
    model_items = [i for i in items if i['item_type'] == 'model']
    # At least the CRISPR model should match
    crispr_models = [i for i in model_items if 'crispr' in i['hf_id'].lower()]
    assert len(crispr_models) >= 1


def test_huggingface_paper_types():
    """Test that papers have correct item_type."""
    papers = load_papers()
    items, _ = huggingface.search_huggingface(
        topic="CRISPR gene editing",
        from_date="2025-01-01",
        to_date="2025-01-31",
        mock_models=[],
        mock_papers=papers,
    )
    paper_items = [i for i in items if i['item_type'] == 'paper']
    assert len(paper_items) >= 1


def test_huggingface_date_filter():
    """Test that items outside date range are excluded."""
    models = load_models()
    items, _ = huggingface.search_huggingface(
        topic="CRISPR",
        from_date="2025-01-13",
        to_date="2025-01-31",
        mock_models=models,
        mock_papers=[],
    )
    # Only items from 2025-01-13 or later should be included
    for item in items:
        if item.get('date'):
            assert item['date'] >= "2025-01-13"
