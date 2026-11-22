import unittest

from project.bot.src.chatbot.query_processor import QueryProcessor
from project.bot.src.chatbot.schemas import ConversationState, SearchRequest


class QueryProcessorTests(unittest.TestCase):
    def setUp(self):
        self.processor = QueryProcessor()

    def test_single_turn_entity_extraction(self):
        msg = "Tìm quán cafe học bài ở Cầu Giấy dưới 50k"
        res = self.processor.process(msg, ConversationState())

        self.assertEqual(res.intent, 'location_recommendation')
        self.assertIsNone(res.clarification)
        self.assertEqual(res.request.category, 'ca-phe')
        self.assertEqual(res.request.location, 'Cầu Giấy')
        self.assertEqual(res.request.budget_max, 50000)
        self.assertIn('học tập', res.request.preferences)

    def test_multi_turn_constraint_retention_and_clear(self):
        # Turn 1
        res1 = self.processor.process("Quán ăn ở Tây Hồ", ConversationState())
        state1 = ConversationState(constraints=res1.request)
        self.assertEqual(state1.constraints.category, 'an-uong')
        self.assertEqual(state1.constraints.location, 'Tây Hồ')

        # Turn 2: change location to Ba Đình, category should be preserved
        res2 = self.processor.process("Đổi sang Ba Đình", state1)
        self.assertEqual(res2.request.category, 'an-uong')
        self.assertEqual(res2.request.location, 'Ba Đình')

        # Turn 3: add budget
        state2 = ConversationState(constraints=res2.request)
        res3 = self.processor.process("Dưới 100k nhé", state2)
        self.assertEqual(res3.request.category, 'an-uong')
        self.assertEqual(res3.request.location, 'Ba Đình')
        self.assertEqual(res3.request.budget_max, 100000)

        # Turn 4: remove budget limit
        state3 = ConversationState(constraints=res3.request)
        res4 = self.processor.process("Không giới hạn giá nữa", state3)
        self.assertEqual(res4.request.category, 'an-uong')
        self.assertEqual(res4.request.location, 'Ba Đình')
        self.assertIsNone(res4.request.budget_max)

    def test_ambiguous_hus_reference(self):
        res = self.processor.process("Tìm quán ăn quanh ĐH Khoa học Tự nhiên HUS", ConversationState())
        self.assertEqual(res.intent, 'clarification')
        self.assertIsNotNone(res.clarification)
        self.assertIn("334 Nguyễn Trãi", res.clarification)
        self.assertIn("19 Lê Thánh Tông", res.clarification)

    def test_explicit_ui_filter_conflict(self):
        res = self.processor.process(
            "Tìm quán bún ở Cầu Giấy",
            ConversationState(),
            explicit_filters={"district": "Hoàn Kiếm"},
        )
        self.assertEqual(res.intent, 'clarification')
        self.assertIsNotNone(res.clarification)
        self.assertIn("Hoàn Kiếm", res.clarification)
        self.assertIn("Cầu Giấy", res.clarification)

    def test_reset_conversation(self):
        initial = SearchRequest(category='ca-phe', location='Tây Hồ')
        state = ConversationState(constraints=initial)
        res = self.processor.process("Bắt đầu lại từ đầu", state)
        self.assertEqual(res.intent, 'reset')
        self.assertEqual(res.request, SearchRequest())

    def test_no_false_category_from_substrings_or_street_names(self):
        # 'ăn' should not match inside 'Văn Miếu' or 'Lăng Bác' or 'Hoàng Thành'
        self.assertEqual(self.processor.process("Đi thăm Văn Miếu", ConversationState()).request.category, 'tam-linh')
        self.assertEqual(self.processor.process("Tham quan Lăng Bác", ConversationState()).request.category, 'di-tich')
        self.assertEqual(self.processor.process("Đi thăm Hoàng Thành", ConversationState()).request.category, 'di-tich')
        # Street / district names containing 'chùa' or 'hồ' are location evidence only
        tây_ho = self.processor.process("Tìm chỗ yên tĩnh ở Tây Hồ", ConversationState())
        self.assertEqual(tây_ho.request.location, 'Tây Hồ')
        self.assertIsNone(tây_ho.request.category)
        chua_lang = self.processor.process("Chỗ ngồi yên tĩnh ở Chùa Láng", ConversationState())
        self.assertEqual(chua_lang.request.location, 'Đống Đa')
        self.assertIsNone(chua_lang.request.category)
        ho_tung_mau = self.processor.process("Tìm chỗ ở Hồ Tùng Mậu", ConversationState())
        self.assertEqual(ho_tung_mau.request.location, 'Cầu Giấy')
        self.assertIsNone(ho_tung_mau.request.category)
        hang_chao = self.processor.process("Quán bún ở phố Hàng Cháo", ConversationState())
        self.assertEqual(hang_chao.request.category, 'an-uong')
        self.assertNotIn('dish:cháo', hang_chao.request.hard_constraints)

    def test_budget_units_bounds_and_non_money_guards(self):
        self.assertEqual(self.processor.process("dưới 1 triệu", ConversationState()).request.budget_max, 1000000)
        self.assertEqual(self.processor.process("dưới 1tr5", ConversationState()).request.budget_max, 1500000)
        self.assertEqual(self.processor.process("50k", ConversationState()).request.budget_max, 50000)

        min_only = self.processor.process("trên 100k", ConversationState()).request
        self.assertEqual(min_only.budget_min, 100000)
        self.assertIsNone(min_only.budget_max)

        ranged = self.processor.process("từ 50k đến 100k", ConversationState()).request
        self.assertEqual((ranged.budget_min, ranged.budget_max), (50000, 100000))

        for msg in ("tầm 7 giờ tối đi ăn", "khoảng 3 người", "quán ở 1050 đường láng"):
            req = self.processor.process(msg, ConversationState()).request
            self.assertIsNone(req.budget_min, msg)
            self.assertIsNone(req.budget_max, msg)

    def test_preference_word_boundaries_negation_and_setting_switch(self):
        # Word boundary prevents matching 'date' inside 'update'
        self.assertEqual(self.processor.process("update menu", ConversationState()).request.preferences, ())
        # Misleading preference terms should not misclassify
        self.assertNotIn('gia đình', self.processor.process("quán ăn ấm cúng", ConversationState()).request.preferences)
        self.assertNotIn('24/7', self.processor.process("đi muộn", ConversationState()).request.preferences)

        # Negation removes or skips preference, while "không ồn" remains "yên tĩnh"
        self.assertIn('yên tĩnh', self.processor.process("quán không ồn", ConversationState()).request.preferences)
        t1 = self.processor.process("tìm cafe yên tĩnh", ConversationState()).request
        t2 = self.processor.process("không cần yên tĩnh nữa", ConversationState(constraints=t1)).request
        self.assertNotIn('yên tĩnh', t2.preferences)

        # Setting replacement removes conflicting outdoor category & preference
        outdoor = self.processor.process("Tìm chỗ đi dạo ngoài trời", ConversationState()).request
        self.assertEqual(outdoor.setting, 'outdoor')
        indoor = self.processor.process("Chỉ tìm trong nhà", ConversationState(constraints=outdoor)).request
        self.assertEqual(indoor.setting, 'indoor')
        self.assertNotIn('ngoài trời', indoor.preferences)
        self.assertIsNone(indoor.category)

    def test_category_precedence_and_ui_category_conflict(self):
        swim = self.processor.process("đi bơi ở hồ bơi", ConversationState()).request
        self.assertIn('activity:bơi', swim.hard_constraints)
        food_hangout = self.processor.process("đi chơi ăn uống ở tây hồ", ConversationState()).request
        self.assertEqual(food_hangout.category, 'an-uong')
        self.assertEqual(food_hangout.location, 'Tây Hồ')

        conflict = self.processor.process(
            "Tìm quán phở",
            ConversationState(),
            explicit_filters={"category": "ca-phe"},
        )
        self.assertEqual(conflict.intent, 'clarification')
        self.assertIn("Cà phê", conflict.clarification)

    def test_district_transitions_overlapping_streets_hus_party_weather(self):
        self.assertEqual(self.processor.process("từ cầu giấy sang hoàn kiếm", ConversationState()).request.location, 'Hoàn Kiếm')
        self.assertEqual(self.processor.process("từ hoàn kiếm sang cầu giấy", ConversationState()).request.location, 'Cầu Giấy')
        self.assertEqual(self.processor.process("quán ở phố minh khai", ConversationState()).request.location, 'Hai Bà Trưng')
        self.assertEqual(self.processor.process("quán ở phường minh khai", ConversationState()).request.location, 'Bắc Từ Liêm')
        self.assertEqual(self.processor.process("gần HUS cơ sở 1", ConversationState()).request.location, 'Hoàn Kiếm')
        self.assertEqual(self.processor.process("gần HUS cơ sở 2", ConversationState()).request.location, 'Thanh Xuân')

        self.assertEqual(self.processor.process("nhóm 5 người", ConversationState()).request.party_size, 5)
        self.assertEqual(self.processor.process("hai người", ConversationState()).request.party_size, 2)

        rain = self.processor.process("Trời đang mưa, tìm chỗ đi chơi", ConversationState()).request
        self.assertEqual((rain.weather, rain.weather_source), ('mưa', 'user'))
        cleared = self.processor.process("Tạnh mưa rồi, tìm chỗ đi chơi", ConversationState(constraints=rain)).request
        self.assertIsNone(cleared.weather)
        self.assertIsNone(cleared.weather_source)


if __name__ == '__main__':
    unittest.main()
