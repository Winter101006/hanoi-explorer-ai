"""Aggregate explicit human labels. Missing labels remain unassessed."""
import math


def generation(rows):
    labelled = [row['annotations'] for row in rows if row.get('annotations') is not None]
    total = supported = 0
    relevance = []
    for item in labelled:
        counts = [item[key] for key in ('total_claims', 'supported_claims', 'unsupported_claims')]
        if any(type(value) is not int or value < 0 for value in counts) or counts[1] + counts[2] != counts[0]:
            raise ValueError('Each claim needs a supported/unsupported label')
        score = item['relevance']
        if type(score) not in (int, float) or not 0 <= score <= 1:
            raise ValueError('Relevance must be in [0,1]')
        total += counts[0]
        supported += counts[1]
        relevance.append(score)
    return {'labelled_answers': len(labelled), 'labelled_claims': total,
            'groundedness': supported / total if total else None,
            'hallucination_rate': (total - supported) / total if total else None,
            'answer_relevance': sum(relevance) / len(relevance) if relevance else None}


def conversation(rows):
    values = [row['passed'] for row in rows if row.get('passed') is not None]
    if any(type(value) is not bool for value in values):
        raise ValueError('passed must be boolean or null')
    return {'labelled_cases': len(values), 'pass_rate': sum(values) / len(values) if values else None}


def retrieval(rows, k=5):
    if k < 1:
        raise ValueError('k must be positive')
    results = []
    for row in rows:
        labels = row.get('relevance')
        if labels is None:
            continue
        if any(type(grade) is not int or not 0 <= grade <= 3 for grade in labels.values()):
            raise ValueError('Relevance labels must be integer grades 0–3')
        ids = list(dict.fromkeys(row['predicted']))[:k]
        relevant = {pid for pid, grade in labels.items() if grade > 0}
        hits = len(set(ids) & relevant)
        dcg = sum((2 ** labels.get(pid, 0) - 1) / math.log2(i + 2) for i, pid in enumerate(ids))
        ideal = sum((2 ** grade - 1) / math.log2(i + 2)
                    for i, grade in enumerate(sorted(labels.values(), reverse=True)[:k]))
        results.append({'precision': hits / k, 'recall': hits / len(relevant) if relevant else None,
                        'ndcg': dcg / ideal if ideal else None})
    means = {}
    for key in ('precision', 'recall', 'ndcg'):
        values = [row[key] for row in results if row[key] is not None]
        means[key] = sum(values) / len(values) if values else None
        means[key + '_labelled'] = len(values)
    return means


def recommendation(rows):
    result = {}
    for key in ('preference_match', 'budget_satisfied', 'location_satisfied'):
        values = [row[key] for row in rows if row.get(key) is not None]
        if any(type(value) not in (int, float, bool) or not 0 <= value <= 1 for value in values):
            raise ValueError('Constraint labels must be in [0,1]')
        result[key] = sum(values) / len(values) if values else None
        result[key + '_labelled'] = len(values)
    return result
