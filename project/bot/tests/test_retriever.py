import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock

from project.bot.src.chatbot.config import Settings
from project.bot.src.chatbot.retriever import Retriever, normalize_district_name
from project.bot.src.chatbot.schemas import (
    DataQuality,
    Place,
    PriceInfo,
    RawPlace,
    SearchRequest,
)


class RetrieverTests(unittest.TestCase):
    def setUp(self):
        self.fixtures_path = Path(__file__).parent / 'fixtures/contracts.json'
        data = json.loads(self.fixtures_path.read_text(encoding='utf-8'))
        raw_places = [RawPlace.from_dict(row) for row in data['places']]

        self.places = [
            Place(
                source=raw,
                normalized_category_code=raw.category_code if raw.category_code != 'tam-linh' else 'an-uong',
                price=PriceInfo(status='parsed', minimum=30000, maximum=60000),
                quality=DataQuality(address_precision='district_only'),
            )
            for raw in raw_places
        ]

        self.mock_settings = Settings(
            data_path=Path('dummy.json'),
            chroma_path=Path('dummy_chroma'),
            collection='test_coll',
            retrieval_k=5,
            recommendation_k=2,
        )

        self.mock_chroma = MagicMock()
        self.mock_embedder = MagicMock()
        self.mock_embedder.encode_query.return_value = [0.1] * 384

        self.retriever = Retriever(
            settings=self.mock_settings,
            chroma_manager=self.mock_chroma,
            embedding_manager=self.mock_embedder,
            places=self.places,
        )

    def test_normalize_district(self):
        self.assertEqual(normalize_district_name('quận Cầu Giấy'), 'Cầu Giấy')
        self.assertEqual(normalize_district_name('Tây Hồ'), 'Tây Hồ')
        self.assertIsNone(normalize_district_name('Một nơi xa xôi'))

    def test_retriever_with_filters(self):
        self.mock_chroma.search.return_value = [
            {
                'id': 'test_cafe',
                'distance': 0.15,
                'semantic_score': 0.85,
                'metadata': {'normalized_category_code': 'ca-phe', 'district': 'Cầu Giấy'},
                'document': 'test doc',
            }
        ]

        req = SearchRequest(
            query='cafe học bài',
            category='ca-phe',
            location='Cầu Giấy',
            preferences=('study',),
        )

        results = self.retriever.retrieve(req)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].place.source.id, 'test_cafe')
        self.assertAlmostEqual(results[0].semantic_score, 0.85)
        self.assertTrue(len(results[0].evidence) >= 1)

    def test_exclude_ids(self):
        self.mock_chroma.search.return_value = [
            {
                'id': 'test_cafe',
                'distance': 0.2,
                'semantic_score': 0.8,
                'metadata': {},
                'document': '',
            }
        ]

        req = SearchRequest(
            query='cafe',
            exclude_ids=('test_cafe',),
        )

        results = self.retriever.retrieve(req)
        self.assertEqual(len(results), 0)


if __name__ == '__main__':
    unittest.main()
