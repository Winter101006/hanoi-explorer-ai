import json
from pathlib import Path
import unittest

from project.bot.src.chatbot.config import BOT_DIR, load_settings
from project.bot.src.chatbot.schemas import (
    ChatbotResponse, PriceInfo, QueryUpdate, RawPlace, Recommendation, SearchRequest,
)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads((Path(__file__).parent / 'fixtures/contracts.json').read_text(encoding='utf-8'))

    def test_source_and_fixture_validation(self):
        source = json.loads((BOT_DIR / 'data/hanoi_places_cleaned.json').read_text(encoding='utf-8'))
        records = [RawPlace.from_dict(row) for row in source + self.fixture['places']]
        self.assertEqual(len(records), len(source) + 2)
        self.assertEqual(records[-1].category_code, 'tam-linh')

    def test_coordinate_and_tag_validation(self):
        for change in ({'latitude': float('nan')}, {'longitude': 181}, {'tags': 'quiet'}, {'id': ''}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                RawPlace.from_dict(self.fixture['places'][0] | change)

    def test_context_updates_preserve_and_clear_constraints(self):
        state = SearchRequest()
        for turn in self.fixture['conversation']:
            values = dict(turn['values'])
            if 'preferences' in values:
                values['preferences'] = tuple(values['preferences'])
            state = QueryUpdate(values, tuple(turn['clear_fields'])).apply(state)
        self.assertEqual(state.category, 'ca-phe')
        self.assertEqual(state.location, 'Tây Hồ')
        self.assertEqual(state.preferences, ('study', 'quiet'))
        self.assertIsNone(state.budget_max)
        self.assertEqual(QueryUpdate(reset=True).apply(state), SearchRequest())

    def test_invalid_context_updates(self):
        for update in (QueryUpdate({'budget_max': None}), QueryUpdate({'budget_max': -1}),
                       QueryUpdate({'location': 'x'}, ('location',)), QueryUpdate({'invented': True})):
            with self.subTest(update=update), self.assertRaises(ValueError):
                update.apply(SearchRequest())

    def test_price_and_score_validation(self):
        with self.assertRaises(ValueError):
            PriceInfo(minimum=50000, maximum=20000)
        for score in (-1, 2, float('nan')):
            with self.subTest(score=score), self.assertRaises(ValueError):
                Recommendation('test_cafe', score)

    def test_generation_ids_must_be_retrieved(self):
        good = Recommendation('test_cafe', .8)
        ChatbotResponse('answer', (good,)).validate_ids({'test_cafe'})
        for recommendations in ((good, good), (Recommendation('test_outside_retrieval', .5),)):
            with self.assertRaises(ValueError):
                ChatbotResponse('answer', recommendations).validate_ids({'test_cafe'})

    def test_config_paths_and_secret(self):
        settings = load_settings({'GEMINI_API_KEY': 'test-secret'})
        self.assertEqual(settings.data_path, BOT_DIR / 'data/hanoi_places_cleaned.json')
        self.assertNotIn('test-secret', repr(settings))

    def test_invalid_config(self):
        for env in ({'RETRIEVAL_K': '0'}, {'WEIGHT_BUDGET': '0.9'}, {'GEMINI_MAX_RETRIES': '-1'},
                    {'RETRIEVAL_K': '2', 'RECOMMENDATION_K': '5'}):
            with self.subTest(env=env), self.assertRaises(ValueError):
                load_settings(env)


if __name__ == '__main__':
    unittest.main()
