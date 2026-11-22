import io
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError

from project.bot.src.chatbot.chatbot import Chatbot
from project.bot.src.chatbot.config import load_settings
from project.bot.src.chatbot.gemini_client import GeminiClient, GeminiError
from project.bot.src.chatbot.memory import ConversationMemory
from project.bot.src.chatbot.query_processor import QueryProcessor
from project.bot.src.chatbot.recommender import Recommender
from project.bot.src.chatbot.schemas import (
    ChatRequest, ConversationState, ConversationTurn, Place, RawPlace,
    PriceInfo, DataQuality, Recommendation, RetrievalResult, SearchRequest,
)
from project.bot.src.web.app import create_app
from project.bot.src.web.services.chat_service import ChatService


def fixture_places():
    rows = json.loads((Path(__file__).parent / 'fixtures/contracts.json').read_text(encoding='utf-8'))['places']
    first = Place(RawPlace.from_dict(rows[0]), 'ca-phe', PriceInfo(30000, 40000, status='parsed'),
                  DataQuality(address_precision='district_only'))
    second = replace(first, source=replace(first.source, id='test_other', name='Quán mẫu B'))
    return [first, second]


class MemoryTests(unittest.TestCase):
    def test_isolation_expiry_capacity_and_bounds(self):
        clock = Mock(return_value=0)
        memory = ConversationMemory(ttl_seconds=10, max_sessions=2, history_turns=2,
                                    max_content_chars=3, clock=clock)
        state = ConversationState(history=tuple(ConversationTurn('user', 'abcdef') for _ in range(5)))
        memory.save('a', state)
        self.assertEqual([t.content for t in memory.get('a').history], ['abc', 'abc'])
        self.assertEqual(memory.get('b'), ConversationState())
        memory.save('b', state)
        memory.save('c', state)
        self.assertEqual(memory.get('a'), ConversationState())
        memory.clear('b')
        self.assertEqual(memory.get('b'), ConversationState())
        clock.return_value = 10
        self.assertEqual(memory.get('c'), ConversationState())

    def test_atomic_turns(self):
        memory = ConversationMemory()
        def increment(_):
            with memory.turn('a'):
                state = memory.get('a')
                memory.save('a', replace(state, constraints=SearchRequest(query=str(int(state.constraints.query or 0) + 1))))
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(increment, range(40)))
        self.assertEqual(memory.get('a').constraints.query, '40')

    def test_returned_states_do_not_mutate_storage(self):
        memory = ConversationMemory()
        memory.save('a', ConversationState())
        self.assertIsNot(memory.get('a'), memory.get('a'))
        with self.assertRaises(ValueError):
            memory.get('')


class GeminiTests(unittest.TestCase):
    def setUp(self):
        self.settings = load_settings({'GEMINI_MODEL':'test-model','GEMINI_API_KEY':'secret-test'})

    def response(self, content, finish='STOP'):
        return io.BytesIO(json.dumps({'candidates':[{'finishReason':finish,
            'content':{'parts':[{'text':json.dumps(content)}]}}]}).encode())

    def test_retry_and_request_shape(self):
        opener = Mock(side_effect=[HTTPError('url',429,'limited',{},None),self.response({'answer':'ok'})])
        sleep = Mock()
        result = GeminiClient(self.settings,opener,sleep).generate_answer('hello')
        self.assertEqual(result, {'answer':'ok'})
        self.assertEqual(opener.call_count,2)
        sleep.assert_called_once_with(1)
        request = opener.call_args.args[0]
        self.assertNotIn('secret-test',request.full_url)
        self.assertEqual(json.loads(request.data)['generationConfig']['responseMimeType'],'application/json')
        self.assertEqual(opener.call_args.kwargs['timeout'],30)

    def test_permanent_failure_and_missing_config(self):
        opener = Mock(side_effect=HTTPError('url',403,'secret-test',{},None))
        with self.assertRaises(GeminiError) as error:
            GeminiClient(self.settings,opener).extract_query('x')
        self.assertNotIn('secret-test',str(error.exception))
        self.assertEqual(opener.call_count,1)
        with self.assertRaises(GeminiError):
            GeminiClient(load_settings({}),opener).generate_answer('x')
        self.assertEqual(opener.call_count,1)

    def test_network_exhaustion(self):
        opener = Mock(side_effect=TimeoutError())
        with self.assertRaises(GeminiError):
            GeminiClient(self.settings,opener,Mock()).generate_answer('x')
        self.assertEqual(opener.call_count,3)

    def test_malformed_and_blocked_response(self):
        for response in (io.BytesIO(b'not-json'),io.BytesIO(b'{}'), self.response([]),
                         self.response({'answer':'partial'},'MAX_TOKENS')):
            with self.subTest(response=response), self.assertRaises(GeminiError):
                GeminiClient(self.settings,Mock(return_value=response)).generate_answer('x')


class ChatbotTests(unittest.TestCase):
    def setUp(self):
        self.places = fixture_places()
        self.retriever = Mock()
        self.retriever.retrieve.return_value = [RetrievalResult(p,.9) for p in self.places]
        self.gemini = Mock()
        self.gemini.generate_answer.return_value = {'answer':'Hai quán mẫu yên tĩnh theo mô tả.',
            'recommendation_ids':['test_cafe','test_other'],'follow_up':None}
        self.memory = ConversationMemory()
        self.bot = Chatbot(QueryProcessor(),self.retriever,Recommender(),self.gemini,
                           self.memory,places=self.places)

    def test_multi_turn_with_real_ws2(self):
        self.bot.respond(ChatRequest('Cafe học bài ở Cầu Giấy dưới 50k',session_id='a'))
        self.bot.respond(ChatRequest('Yên tĩnh hơn',session_id='a'))
        state = self.memory.get('a')
        self.assertEqual(state.constraints.location,'Cầu Giấy')
        self.assertEqual(state.constraints.budget_max,50000)
        self.assertIn('yên tĩnh',state.constraints.preferences)
        self.assertEqual(len(state.history),4)
        self.bot.respond(ChatRequest('Không giới hạn giá nữa',session_id='a'))
        self.assertIsNone(self.memory.get('a').constraints.budget_max)
        self.assertEqual(self.memory.get('b'),ConversationState())

    def test_dish_change_budget_and_neighborhood(self):
        processor = QueryProcessor()
        first = processor.process('phở bò gia truyền phố cổ dưới 60k', ConversationState()).request
        follow = processor.process('còn bánh cuốn thì sao?', ConversationState(constraints=first)).request
        self.assertEqual(set(follow.hard_constraints), {'dish:bánh cuốn', 'area:phố cổ'})
        self.assertEqual((follow.location, follow.budget_max), ('Hoàn Kiếm', 60000))
        moved = processor.process('ở Cầu Giấy', ConversationState(constraints=follow)).request
        self.assertEqual(moved.hard_constraints, ('dish:bánh cuốn',))
        noodle, rolls = [replace(p, normalized_category_code='an-uong',
            source=replace(p.source, name=name, description=desc)) for p, name, desc in
            zip(self.places, ('Phở tái', 'Bánh cuốn'), ('', 'Có cả phở cuốn thịt bò'))]
        hits = [RetrievalResult(rolls, 1), RetrievalResult(noodle, .6)]
        self.assertEqual([r.place_id for r in Recommender().rank(first, hits)], [noodle.source.id])
        self.assertEqual([r.place_id for r in Recommender().rank(follow, hits)], [rolls.source.id])

    def test_conversation_source_and_internal_labels(self):
        with self.assertLogs('project.bot.src.chatbot.chatbot', level='INFO') as logs:
            response = self.bot.respond(ChatRequest('Cafe Cầu Giấy'))
        self.assertEqual(response.answer, self.gemini.generate_answer.return_value['answer'])
        self.assertIn('source=gemini', logs.output[-1])
        self.gemini.generate_answer.return_value['answer'] = 'Khớp danh mục ca-phe'
        with self.assertLogs('project.bot.src.chatbot.chatbot') as logs:
            response = self.bot.respond(ChatRequest('Cafe Cầu Giấy'))
        self.assertIn('source=fallback', logs.output[-1])
        self.assertNotIn('ca-phe', response.answer)
        self.assertNotIn('Cafe Cầu Giấy', str(logs.output))

    def test_generated_price_and_rating_require_evidence(self):
        for claim in ('Giá 987.000 đồng.', 'Quán được 4,9 sao.'):
            with self.subTest(claim=claim):
                self.gemini.generate_answer.return_value['answer'] = claim
                response = self.bot.respond(ChatRequest('Cafe Cầu Giấy'))
                self.assertNotIn(claim, response.answer)

    def test_reset_and_clarification_skip_retrieval(self):
        response = self.bot.respond(ChatRequest('Gần HUS',session_id='a'))
        self.assertIn('cơ sở',response.answer)
        self.retriever.retrieve.assert_not_called()
        self.bot.respond(ChatRequest('bắt đầu lại',session_id='a'))
        self.assertEqual(self.memory.get('a').constraints,SearchRequest())

    def test_movie_plan_with_separate_dining_budget(self):
        query = QueryProcessor().process(
            'Tôi muốn đi xem phim với gái, tìm quán dưới 50 nghìn ở Thanh Xuân', ConversationState()).request
        self.assertEqual((query.category, query.location, query.budget_max), ('an-uong', 'Thanh Xuân', 50000))
        self.assertNotIn('activity:xem phim', query.hard_constraints)
        cinema = QueryProcessor().process('Tìm rạp xem phim dưới 50k ở Thanh Xuân', ConversationState()).request
        self.assertIn('activity:xem phim', cinema.hard_constraints)

    def test_other_food_releases_only_food_filter(self):
        processor = QueryProcessor()
        state = ConversationState()
        for text, dishes in [('Quán bún chó ở Thanh Xuân dưới 100k', ['dish:bún chó']),
                             ('Các món ăn miền Tây thì sao?', ['dish:miền tây']),
                             ('Thế có món gì khác?', []), ('Món khác', []),
                             ('Ăn phở bò thì sao?', ['dish:phở bò'])]:
            query = processor.process(text, state).request
            self.assertEqual(list(query.hard_constraints), dishes)
            self.assertEqual((query.category, query.location, query.budget_max), ('an-uong', 'Thanh Xuân', 100000))
            state = replace(state, constraints=query)

    def test_unattested_dish_never_returns_generic_restaurants(self):
        restaurant = replace(self.places[0], normalized_category_code='an-uong',
                             source=replace(self.places[0].source, district='Thanh Xuân',
                                            name='Sumo BBQ', description='Quán chuyên thịt nướng'))
        self.retriever.retrieve.return_value = [RetrievalResult(restaurant, 1)]
        for text in ('quán bún chó ở thanh xuân', 'tìm quán món xyzqax ở Thanh Xuân'):
            response = self.bot.respond(ChatRequest(text))
            self.assertFalse(response.recommendations)
            self.assertIn('chưa tìm được', response.answer)
        self.gemini.generate_answer.assert_not_called()

    def test_tourism_area_and_gemini_cards(self):
        cafe, other = self.places
        site = replace(other, normalized_category_code='ngoai-troi',
                       source=replace(other.source, name='Khu du lịch sinh thái Vườn Nhãn Gia Lâm',
                                      district='Long Biên'))
        second = replace(site, source=replace(site.source, id='site_2', name='Khu du lịch sinh thái mẫu'))
        self.retriever.retrieve.return_value = [RetrievalResult(p, .9) for p in (cafe, site, second)]
        response = self.bot.respond(ChatRequest('Gợi ý khu du lịch ở Gia Lâm'))
        self.assertFalse(response.recommendations)
        self.assertIn('Gia Lâm', response.answer)
        self.gemini.generate_answer.assert_not_called()
        self.gemini.generate_answer.return_value = {
            'answer': 'Bạn có thể ghé khu du lịch sinh thái mẫu.',
            'recommendation_ids': ['site_2'],
        }
        response = self.bot.respond(ChatRequest('Gợi ý khu du lịch ở Long Biên'))
        self.assertEqual([r.place_id for r in response.recommendations], ['site_2'])
        self.gemini.generate_answer.side_effect = GeminiError('offline')
        response = self.bot.respond(ChatRequest('Gợi ý khu du lịch'))
        self.assertEqual({r.place_id for r in response.recommendations}, {site.source.id, 'site_2'})

    def test_tourism_followup_broadens_only_for_generic_alternatives(self):
        cafe = self.places[0]
        venues = (('site', 'Khu sinh thái Đầm Tranh', 'ngoai-troi', 'Long Biên'),
                  ('site2', 'Khu du lịch sinh thái mẫu', 'ngoai-troi', 'Long Biên'),
                  ('cinema', 'Rạp chiếu phim', 'giai-tri', 'Long Biên'),
                  ('park', 'Công viên', 'ngoai-troi', 'Long Biên'),
                  ('other_district', 'Rạp chiếu phim khác', 'giai-tri', 'Cầu Giấy'))
        places = [replace(cafe, normalized_category_code=code,
                          source=replace(cafe.source, id=pid, name=name, district=district))
                  for pid, name, code, district in venues]
        food = replace(cafe, source=replace(cafe.source, district='Long Biên'))
        self.retriever.retrieve.return_value = [RetrievalResult(p, .9) for p in [food, *places]]
        self.gemini.generate_answer.side_effect = GeminiError('offline')
        history = (ConversationTurn('user', 'Tìm khu du lịch ở Gia Lâm'),
                   ConversationTurn('user', 'Ở Long Biên thì sao?'),
                   ConversationTurn('assistant', 'Ghé Đầm Tranh.', ('site',)))
        for message in ('Long Biên còn gì khác chơi không?', 'Còn chỗ nào khác ở Long Biên không?'):
            response = self.bot.respond(ChatRequest(message, history=history))
            self.assertEqual({r.place_id for r in response.recommendations}, {'cinema', 'park'})
        response = self.bot.respond(ChatRequest('Còn khu du lịch nào khác?', history=history))
        self.assertEqual([r.place_id for r in response.recommendations], ['site2'])
        response = self.bot.respond(ChatRequest('Còn chỗ nào khác không?', history=history + (
            ConversationTurn('user', 'Long Biên còn gì khác chơi không?'),
            ConversationTurn('assistant', 'Đi xem phim hoặc đi công viên.', ('cinema', 'park')),
        )))
        self.assertFalse(response.recommendations)

    def test_alternative_search_keeps_area_budget_and_explicit_type(self):
        processor = QueryProcessor()
        for area in ('Tây Hồ', 'Hoàn Kiếm', 'Cầu Giấy'):
            state = ConversationState(constraints=processor.process(
                f'Tìm khu du lịch ở {area} dưới 100k', ConversationState()).request)
            for message in ('Còn chỗ nào khác không?', 'Có gì chơi khác không?', 'Đổi địa điểm nhé'):
                search = processor.process(message, state).request
                self.assertEqual((search.location, search.budget_max), (area, 100000))
                self.assertIn('tourism:alternative', search.hard_constraints)
            cinema = processor.process('Thế còn rạp chiếu phim nào khác?', state).request
            self.assertEqual(cinema.category, 'giai-tri')
            self.assertNotIn('tourism:site', cinema.hard_constraints)

        cafe = ConversationState(constraints=processor.process(
            'Tìm quán cafe ở Cầu Giấy', ConversationState()).request)
        self.assertEqual(processor.process('Còn quán nào khác?', cafe).request.category, 'ca-phe')
        self.assertIn('tourism:alternative', processor.process(
            'Còn gì khác chơi không?', cafe).request.hard_constraints)

    def test_routes_and_pending_activity(self):
        response = self.bot.respond(ChatRequest('Tôi muốn chơi bida gần HUS', session_id='a'))
        self.assertNotIn('hai bạn', response.answer.lower())
        for message in ('Bạn là ai?', 'Hôm nay thời tiết thế nào?', 'Tôi muốn đi nhà nghỉ'):
            self.assertFalse(self.bot.respond(ChatRequest(message, session_id='a')).recommendations)
        self.retriever.retrieve.assert_not_called()
        response = self.bot.respond(ChatRequest('Nguyễn Trãi', session_id='a'))
        search = self.retriever.retrieve.call_args.args[0]
        self.assertIn('activity:bida', search.hard_constraints)
        self.assertEqual(search.location, 'Thanh Xuân')
        self.assertFalse(response.recommendations)

    def test_social_replies_follow_the_conversation(self):
        intro = self.bot.respond(ChatRequest('Bạn là ai?', session_id='new'))
        self.assertIn('Hanoi Explorer AI', intro.answer)
        self.bot.respond(ChatRequest('Tìm chỗ chơi bida gần HUS', session_id='active'))
        reply = self.bot.respond(ChatRequest('Chào bạn!', session_id='active'))
        self.assertIn('Nguyễn Trãi', reply.answer)
        thanks = self.bot.respond(ChatRequest('Cảm ơn bạn nhé!', session_id='active'))
        self.assertNotIn('?', thanks.answer)
        self.retriever.retrieve.assert_not_called()

    def test_party_is_explicit_and_isolated(self):
        for sid, message, size in [('a','Tôi muốn đi cafe',None), ('b','Tôi muốn đi chơi',None),
                                   ('a','Tôi đi một mình',1), ('b','Tôi đi với 3 người bạn',4)]:
            self.bot.respond(ChatRequest(message, session_id=sid))
            self.assertEqual(self.memory.get(sid).constraints.party_size, size)
            self.assertNotIn('hẹn hò', self.memory.get(sid).constraints.preferences)
        self.assertEqual(self.memory.get('a').constraints.party_size, 1)

    def test_generation_checks_group_and_duplicate_question(self):
        self.gemini.generate_answer.return_value['answer'] = 'Hai bạn có thể đến đây.'
        self.assertNotIn('hai bạn', self.bot.respond(ChatRequest('Cafe')).answer.lower())
        self.gemini.generate_answer.return_value.update(answer='Bạn thích quán nào?', follow_up='Bạn sẽ chọn đâu?')
        self.assertIsNone(self.bot.respond(ChatRequest('Cafe')).follow_up)

    def test_clarification_keeps_original_request(self):
        self.bot.respond(ChatRequest('Cafe học bài gần HUS dưới 50k',session_id='a'))
        self.bot.respond(ChatRequest('Nguyễn Trãi',session_id='a'))
        state = self.memory.get('a')
        self.assertEqual(state.constraints.category,'ca-phe')
        self.assertEqual(state.constraints.budget_max,50000)
        self.assertEqual(state.constraints.location,'Thanh Xuân')

    def test_no_results_and_strict_area_budget(self):
        bad_area = replace(self.places[0],source=replace(self.places[0].source,district='Tây Hồ'))
        bad_price = replace(self.places[1],price=PriceInfo(30000,60000,status='parsed'))
        self.retriever.retrieve.return_value = [RetrievalResult(p,.9) for p in (bad_area,bad_price)]
        response = self.bot.respond(ChatRequest('Cafe Cầu Giấy dưới 50k'))
        self.assertFalse(response.recommendations)
        self.gemini.generate_answer.assert_not_called()

    def test_api_distinguishes_strict_and_inclusive_budget_caps(self):
        cafe = replace(self.places[0], price=PriceInfo(30000, 45000, status='parsed'))
        self.retriever.retrieve.return_value = [RetrievalResult(cafe, .9)]
        self.gemini.generate_answer.side_effect = GeminiError('offline')
        service = ChatService(settings=load_settings({}), bot=self.bot, places=[cafe])
        client = create_app(service=service).test_client()
        for wording, expected in [('dưới 45k', []), ('tối đa 45k', [cafe.source.id])]:
            with self.subTest(wording=wording):
                response = client.post('/api/chat', json={'message': f'Cafe Cầu Giấy {wording}'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual([place['id'] for place in response.json['places']], expected)

    def test_invalid_ids_and_service_failure_fallback(self):
        self.gemini.generate_answer.return_value = {'answer':'invented','recommendation_ids':['unknown']}
        response = self.bot.respond(ChatRequest('Cafe Cầu Giấy'))
        self.assertNotIn('invented',response.answer)
        self.assertIn('Quán mẫu A',response.answer)
        self.gemini.generate_answer.side_effect = GeminiError('unavailable')
        self.assertIn('Quán mẫu A',self.bot.respond(ChatRequest('Cafe Cầu Giấy')).answer)

    def test_legacy_history_and_property_lookup(self):
        history = (ConversationTurn('user','Cafe học bài ở Cầu Giấy dưới 50k'),
                   ConversationTurn('assistant','untrusted metadata',('test_cafe',)))
        response = self.bot.respond(ChatRequest('Địa chỉ chính xác?',history=history))
        self.assertIn('chưa đủ địa chỉ chính xác',response.answer)
        self.retriever.retrieve.assert_not_called()
        self.bot.respond(ChatRequest('Yên tĩnh hơn',history=history))
        self.assertEqual(self.retriever.retrieve.call_args.args[0].location,'Cầu Giấy')

    def test_legacy_campus_clarification(self):
        history = (ConversationTurn('user','Cafe học bài gần HUS dưới 50k'),
                   ConversationTurn('assistant','Bạn muốn cơ sở nào?'))
        self.bot.respond(ChatRequest('Nguyễn Trãi',history=history))
        search = self.retriever.retrieve.call_args.args[0]
        self.assertEqual(search.category,'ca-phe')
        self.assertEqual(search.location,'Thanh Xuân')
        self.assertEqual(search.budget_max,50000)

    def test_exclude_previous_and_error_does_not_save(self):
        self.bot.respond(ChatRequest('Cafe Cầu Giấy',session_id='a'))
        response = self.bot.respond(ChatRequest('Quán khác',session_id='a'))
        self.assertEqual(response.recommendations,())
        self.retriever.retrieve.side_effect = RuntimeError('index failed')
        before = self.memory.get('a')
        with self.assertRaises(RuntimeError):
            self.bot.respond(ChatRequest('Cafe Cầu Giấy',session_id='a'))
        self.assertEqual(self.memory.get('a'),before)
