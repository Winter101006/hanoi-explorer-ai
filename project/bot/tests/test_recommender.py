import json
from pathlib import Path
import unittest

from project.bot.src.chatbot.recommender import Recommender
from project.bot.src.chatbot.schemas import (
    DataQuality,
    Place,
    PriceInfo,
    RawPlace,
    RetrievalResult,
    SearchRequest,
)


class RecommenderTests(unittest.TestCase):
    def setUp(self):
        self.fixtures_path = Path(__file__).parent / 'fixtures/contracts.json'
        data = json.loads(self.fixtures_path.read_text(encoding='utf-8'))
        raw_places = [RawPlace.from_dict(row) for row in data['places']]

        self.place1 = Place(
            source=raw_places[0],
            normalized_category_code='ca-phe',
            price=PriceInfo(status='parsed', minimum=30000, maximum=60000),
            quality=DataQuality(address_precision='district_only'),
        )

        self.place2 = Place(
            source=raw_places[1],
            normalized_category_code='an-uong',
            price=PriceInfo(status='parsed', minimum=0, maximum=0),
            quality=DataQuality(category_conflict=True, address_precision='area'),
        )

        self.recommender = Recommender()

    def test_ranking_multi_factor_weights(self):
        c1 = RetrievalResult(place=self.place1, semantic_score=0.8)
        c2 = RetrievalResult(place=self.place2, semantic_score=0.6)

        req = SearchRequest(
            location='Cầu Giấy',
            budget_max=50000,
            preferences=('học tập',),
        )

        ranked = self.recommender.rank(req, [c1, c2], limit=2)
        self.assertEqual(len(ranked), 2)
        self.assertEqual(ranked[0].place_id, 'test_cafe')
        self.assertTrue(ranked[0].score >= ranked[1].score)
        self.assertIn('semantic', ranked[0].components)
        self.assertIn('budget', ranked[0].components)

    def test_weight_renormalization_when_criteria_inactive(self):
        # Only semantic and location active; preferences and budget inactive
        c1 = RetrievalResult(place=self.place1, semantic_score=0.9)
        req = SearchRequest(location='Cầu Giấy')

        ranked = self.recommender.rank(req, [c1], limit=1)
        self.assertEqual(len(ranked), 1)
        # Weight sum of semantic (0.4) and location (0.2) = 0.6
        # Normalized weights: 0.4 / 0.6 = 0.6667, 0.2 / 0.6 = 0.3333
        # Expected score: 0.6667 * 0.9 + 0.3333 * 1.0 = 0.6 + 0.3333 = ~0.9333
        self.assertAlmostEqual(ranked[0].score, 0.9333, delta=0.01)

    def test_hard_category_and_budget_constraints(self):
        c1 = RetrievalResult(place=self.place1, semantic_score=0.8)
        c2 = RetrievalResult(place=self.place2, semantic_score=0.9)
        ranked = self.recommender.rank(SearchRequest(category='ca-phe'), [c1, c2], limit=5)
        self.assertEqual([r.place_id for r in ranked], ['test_cafe'])
        ranked = self.recommender.rank(SearchRequest(budget_max=20000), [c1, c2], limit=5)
        self.assertEqual([r.place_id for r in ranked], ['test_conflict'])

    def test_exclude_ids(self):
        c1 = RetrievalResult(place=self.place1, semantic_score=0.9)
        req = SearchRequest(exclude_ids=('test_cafe',))

        ranked = self.recommender.rank(req, [c1], limit=1)
        self.assertEqual(len(ranked), 0)


if __name__ == '__main__':
    unittest.main()


