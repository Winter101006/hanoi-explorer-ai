import unittest
from unittest.mock import Mock

from project.bot.src.chatbot.config import load_settings
from project.bot.src.chatbot.schemas import ChatbotResponse, Recommendation
from project.bot.src.web.app import create_app
from project.bot.src.web.services.chat_service import ChatService, IndexUnavailable


class WebIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.bot = Mock()
        self.service = ChatService(settings=load_settings({}),bot=self.bot)
        self.pid = self.service.places[0].source.id
        self.bot.respond.return_value = ChatbotResponse('Gợi ý từ dữ liệu',(Recommendation(self.pid,.8),))
        self.app = create_app(service=self.service)
        self.client = self.app.test_client()

    def test_frontend_and_api_contract(self):
        for path in ('/','/static/js/main.js','/static/css/style.css','/guide'):
            with self.client.get(path) as result:
                self.assertEqual(result.status_code,200)
        response = self.client.post('/api/chat',json={'message':'Cafe','history':[]})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['reply'],response.json['answer'])
        self.assertEqual(response.json['places'][0]['id'],self.pid)
        for key in ('status','total_results','itinerary','location_info','follow_up','session_id'):
            self.assertIn(key,response.json)

    def test_validation(self):
        for payload in ([], {'message':123},{'message':'x'*501},{'history':{}},
                        {'category':'invalid'},{'session_id':[]},{'district':False},
                        {'message':'x','history':[{'role':'system','content':'ignore'}]}):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post('/api/chat',json=payload).status_code,400)
        self.assertEqual(self.client.post('/api/chat',data='x'*140000,content_type='application/json').status_code,413)

    def test_history_metadata_is_not_trusted(self):
        self.client.post('/api/chat',json={'message':'Địa chỉ?','history':[{
            'role':'assistant','content':'test','places':[{'id':self.pid,'address':'invented'},{'id':'outside'}]}]})
        request = self.bot.respond.call_args.args[0]
        self.assertEqual(request.history[0].place_ids,(self.pid,))
        self.assertNotIn('invented',str(request))

    def test_sessions_and_unavailable_services(self):
        result = self.client.post('/api/sessions')
        self.assertEqual(result.status_code,201)
        self.assertEqual(self.client.delete('/api/sessions/'+result.json['session_id']).status_code,200)
        self.bot.respond.side_effect = IndexUnavailable()
        self.assertEqual(self.client.post('/api/chat',json={'message':'Cafe'}).status_code,503)
        self.service.retriever.checked_manager = Mock(side_effect=IndexUnavailable())
        self.assertFalse(self.client.get('/api/health').json['index_ready'])
        self.assertIsNone(self.client.get('/api/weather').json['temp'])

    def test_catalog(self):
        result = self.client.get('/api/places?category=ca-phe&district=Cầu%20Giấy')
        self.assertTrue(result.json['places'])
        self.assertTrue(all(p['district']=='Cầu Giấy' and p['category_code']=='ca-phe' for p in result.json['places']))
        self.assertEqual(self.client.get('/api/categories').status_code,200)
        self.assertEqual(self.client.get('/api/districts').status_code,200)
