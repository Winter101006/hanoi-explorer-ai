import json
from pathlib import Path
import unittest

from project.bot.src.chatbot.config import BOT_DIR
from project.bot.src.chatbot.data_loader import assess_quality, load, normalize_category, parse_price
from project.bot.src.chatbot.schemas import RawPlace


class DataLoaderTests(unittest.TestCase):
    def setUp(self):
        self.fixtures_path = Path(__file__).parent / 'fixtures/contracts.json'
        self.fixtures = json.loads(self.fixtures_path.read_text(encoding='utf-8'))

    def test_parse_price_formats(self):
        p1 = parse_price('30.000–60.000đ / ly')
        self.assertEqual(p1.status, 'parsed')
        self.assertEqual(p1.minimum, 30000)
        self.assertEqual(p1.maximum, 60000)

        p2 = parse_price('Miễn phí tham quan bên ngoài')
        self.assertEqual(p2.status, 'parsed')
        self.assertEqual(p2.minimum, 0)
        self.assertEqual(p2.maximum, 0)
        self.assertIn('vào cửa/tham quan', p2.conditions)

        p3 = parse_price('Từ 25k')
        self.assertEqual(p3.status, 'parsed')
        self.assertEqual(p3.minimum, 25000)

        p4 = parse_price('Chưa cập nhật')
        self.assertEqual(p4.status, 'unknown')

    def test_category_conflict_and_normalization(self):
        conflict_raw = RawPlace.from_dict(self.fixtures['places'][1])
        self.assertEqual(conflict_raw.category, 'Quán ăn')
        self.assertEqual(conflict_raw.category_code, 'tam-linh')

        norm_code = normalize_category(conflict_raw)
        self.assertEqual(norm_code, 'an-uong')

        quality = assess_quality(conflict_raw)
        self.assertTrue(quality.category_conflict)
        self.assertFalse(quality.coordinates_verified)

    def test_address_precision(self):
        cafe_raw = RawPlace.from_dict(self.fixtures['places'][0])
        quality = assess_quality(cafe_raw)
        self.assertEqual(quality.address_precision, 'district_only')

    def test_load_all_places(self):
        places = load()
        self.assertEqual(len(places), 1691)
        for place in places[:100]:
            self.assertIsNotNone(place.source.id)
            self.assertIsNotNone(place.source.name)
            self.assertIn(place.quality.address_precision, ('district_only', 'area', 'street_or_specific', 'unknown'))

    def test_all_17_food_drink_conflicts_resolved(self):
        places = load()
        conflicts = [p for p in places if p.quality.category_conflict]
        self.assertEqual(len(conflicts), 17)
        for place in places:
            cat = place.source.category.lower()
            if any(w in cat for w in ('quán ăn', 'nhà hàng', 'quán nước')):
                self.assertIn(place.normalized_category_code, ('an-uong', 'ca-phe', None))


if __name__ == '__main__':
    unittest.main()
