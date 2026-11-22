"""Versioned evaluation cases. Only explicitly enabled live cases use Gemini."""
import json
import logging
import os
from dataclasses import asdict
from pathlib import Path
from unittest.mock import Mock

import pytest

from project.bot.src.chatbot.chatbot import Chatbot, conversation_route
from project.bot.src.chatbot.config import load_settings
from project.bot.src.chatbot.gemini_client import GeminiError
from project.bot.src.chatbot.query_processor import QueryProcessor
from project.bot.src.chatbot.recommender import Recommender
from project.bot.src.chatbot.schemas import (
    ConversationState, Place, PriceInfo, RawPlace, RetrievalResult, SearchRequest,
)
from project.bot.src.web.app import create_app
from project.bot.src.web.services.chat_service import ChatService, IndexUnavailable


CASES = json.loads(Path(__file__).with_name('baseline_cases.json').read_text(encoding='utf-8'))


@pytest.fixture
def places():
    rows = [
        ('porridge', 'Quán cháo lòng', 'an-uong', 30000),
        ('rib', 'Quán cháo sườn', 'an-uong', 50000),
        ('beef', 'Quán phở bò', 'an-uong', 60000),
        ('chicken', 'Quán phở gà', 'an-uong', 50000),
        ('grill', 'Quán bún chả', 'an-uong', 50000),
        ('tofu', 'Quán bún đậu', 'an-uong', 40000),
        ('hotpot', 'Lẩu cua', 'an-uong', 100000),
        ('park', 'Công viên', 'ngoai-troi', 0),
        ('cinema', 'Rạp chiếu phim', 'giai-tri', 90000),
        ('pool', 'Câu lạc bộ bida', 'the-thao', 70000),
        ('cafe', 'Cafe yên tĩnh', 'ca-phe', 40000),
    ]
    return [
        Place(RawPlace.from_dict(dict(id=pid, name=name, category_code=category,
              district='Tây Hồ' if pid == 'hotpot' else 'Cầu Giấy',
              weather_fit='Ngoài trời' if pid == 'park' else 'Trong nhà')),
              category, PriceInfo(price, price, status='parsed'))
        for pid, name, category, price in rows
    ]


@pytest.fixture(scope='session')
def real_app():
    return create_app()


def attach_trace(service, trace, monkeypatch):
    for collaborator, method, field in (
        (service.bot.retriever, 'retrieve', 'retrieved_ids'),
        (service.bot.recommender, 'rank', 'ranked_ids'),
    ):
        original = getattr(collaborator, method)

        def observed(*args, original=original, field=field, **kwargs):
            trace['failure_stage'] = 'retrieval' if field == 'retrieved_ids' else 'ranking'
            trace['constraints'] = asdict(args[0])
            output = original(*args, **kwargs)
            trace[field] = [r.place.source.id if field == 'retrieved_ids' else r.place_id for r in output]
            return output

        monkeypatch.setattr(collaborator, method, observed)


def check_fields(actual, expected):
    for key, value in expected.items():
        observed = actual.get(key)
        assert (list(observed) if isinstance(observed, tuple) else observed) == value, key


@pytest.mark.parametrize('case', sorted(CASES, key=lambda c: (c['priority'], c['id'])), ids=lambda c: c['id'])
def test_baseline(case, request, places, real_app, caplog, monkeypatch):
    group, expected, message = case['group'], case['expected'], case['input']
    trace = dict(case, session_context=[], intent=None, constraints=None, retrieved_ids=[],
                 ranked_ids=[], recommendation_ids=[], response_source=None, actual=None,
                 failure_stage='setup', root_cause=None)
    request.node.eval_trace = trace
    caplog.set_level(logging.INFO, logger='project.bot.src.chatbot.chatbot')
    processor = QueryProcessor()
    if group == 'QU':
        trace['failure_stage'] = 'understanding'
        state = ConversationState()
        result = processor.process(message, state)
        trace['intent'] = conversation_route(message.casefold(), state)
        trace['constraints'] = asdict(result.request)
        trace['actual'] = dict(trace['constraints'], intent=result.intent, route=trace['intent'])
        check_fields(trace['actual'], expected)
        return

    if group == 'RT':
        svc = real_app.extensions['chat_service']
        trace['failure_stage'] = 'source_label'
        target = expected['target']
        if expected['label_status'] == 'human_review':
            pytest.skip('Open-ended relevance judgments awaiting human review')
        if target:
            place = svc.by_id[target]
            assert place.source.id == target and place.source.name
            assert place.source.district == case['district']
            assert place.normalized_category_code == case['category']
        trace['failure_stage'] = 'retrieval'
        search = SearchRequest(query=message, category=case['category'], location=case['district'])
        trace['constraints'] = asdict(search)
        if target:
            hits = svc.retriever.retrieve(search)
            trace['retrieved_ids'] = [hit.place.source.id for hit in hits]
            trace['actual'] = trace['retrieved_ids'][:5]
            assert target in trace['actual']
        else:
            monkeypatch.setattr(svc.bot, 'gemini', Mock(generate_answer=Mock(side_effect=GeminiError('offline'))))
            attach_trace(svc, trace, monkeypatch)
            trace['intent'] = conversation_route(message.casefold(), ConversationState())
            response = real_app.test_client().post('/api/chat', json={'message': message})
            trace['actual'] = [r['id'] for r in response.json['places']]
            trace['recommendation_ids'] = trace['actual']
            trace['failure_stage'] = 'no_match'
            assert response.status_code == 200 and not trace['actual']
        return

    gemini = Mock(generate_answer=Mock(side_effect=GeminiError('offline')))
    retriever = Mock(retrieve=Mock(return_value=[RetrievalResult(place, .8) for place in places]))
    settings = load_settings({})
    bot = Chatbot(processor, retriever, Recommender(), gemini, places=places)
    service = ChatService(settings, bot=bot, places=places)
    service.memory = bot.memory
    client = create_app(service=service).test_client()
    attach_trace(service, trace, monkeypatch)

    if group == 'AR':
        trace['failure_stage'] = 'api'
        payload = message['payload']
        if isinstance(payload, dict) and payload.get('simulate_index_down'):
            retriever.retrieve = Mock(side_effect=IndexUnavailable('fixture'))
            payload = {'message': payload['message']}
        response = client.open(message['path'], method=message['method'], json=payload)
        trace['actual'] = {'status': response.status_code}
        check_fields(trace['actual'], expected)
        if response.status_code in (400, 503):
            assert response.json['status'] == 'error' and response.json['places'] == []
        if message['path'] == '/api/weather':
            assert response.json['temp'] is None
        if message['path'].startswith('/api/places'):
            assert response.json['places'] and all(p['district'] == 'Tây Hồ' for p in response.json['places'])
        return

    mode = case.get('mode')
    if mode == 'live':
        if os.getenv('HANOI_EVAL_LIVE_GEMINI') != '1':
            pytest.skip('Opt-in live Gemini evaluation')
        from project.bot.src.chatbot.gemini_client import GeminiClient
        bot.gemini = GeminiClient(load_settings())
        assert bot.gemini.configured, 'Live mode requires GEMINI_MODEL and GEMINI_API_KEY'
    elif mode and mode != 'network':
        payload = {'answer': 'Bạn có thể ghé Cafe yên tĩnh.', 'recommendation_ids': ['cafe']}
        changes = {
            'unknown_id': {'recommendation_ids': ['unretrieved']},
            'jargon': {'answer': 'Khớp danh mục ca-phe'},
            'unsupported_party': {'answer': 'Hai bạn có thể ghé quán.'},
            'unsupported_relationship': {'answer': 'Chỗ này hợp cho buổi hẹn hò.'},
            'duplicate_question': {'answer': 'Bạn thích ngồi đâu?', 'follow_up': 'Bạn muốn chọn chỗ nào?'},
            'empty_answer': {'answer': ' '}, 'wrong_type': {'answer': 12},
            'extra_field': {'ratings': [5]}, 'id_in_prose': {'answer': 'Ghé quán (hn_loc_999) nhé.'},
        }
        payload.update(changes.get(mode, {}))
        if mode == 'missing_answer':
            del payload['answer']
        gemini.generate_answer.side_effect = None
        gemini.generate_answer.return_value = payload

    turns = message if group == 'CM' else [message]
    for turn in turns:
        state = bot.memory.get('eval')
        trace['intent'] = conversation_route(turn.casefold(), state)
        trace['session_context'].append({'message': turn, 'constraints_before': asdict(state.constraints)})
        response = client.post('/api/chat', json={'message': turn, 'session_id': 'eval'})
        assert response.status_code == 200
    body = response.json
    state = bot.memory.get('eval')
    trace['constraints'] = asdict(state.constraints)
    trace['recommendation_ids'] = [place['id'] for place in body['places']]
    for record in reversed(caplog.records):
        if record.name.endswith('.chatbot') and 'source=' in record.getMessage():
            trace['response_source'] = record.getMessage().split('source=', 1)[1].split()[0]
            break
    trace['actual'] = {'reply': body['reply'], 'follow_up': body['follow_up'],
                       'ids': trace['recommendation_ids'], 'source': trace['response_source']}
    if group == 'CM':
        trace['failure_stage'] = 'memory'
        check_fields(trace['constraints'], expected)
        assert bot.memory.get('another-session') == ConversationState()
    elif group == 'CR':
        trace['failure_stage'] = 'constraint_ranking'
        assert set(trace['recommendation_ids']) <= set(expected['ids'])
        assert len(trace['recommendation_ids']) == min(len(expected['ids']), settings.recommendation_k)
    else:
        trace['failure_stage'] = 'generation'
        check_fields(trace['actual'], expected)
        assert trace['recommendation_ids'] == [r['place_id'] for r in body['recommendations']]
        assert len(trace['recommendation_ids']) == len(set(trace['recommendation_ids']))
        assert 'unretrieved' not in body['reply']
        if mode == 'duplicate_question':
            assert body['follow_up'] is None
        if mode == 'id_in_prose':
            assert 'hn_loc_999' not in body['reply']
