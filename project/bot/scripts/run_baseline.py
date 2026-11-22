"""Run pytest and write reproducible baseline reports without printing captured logs."""
import argparse
import json
import os
from collections import Counter
from pathlib import Path

import pytest

from project.bot.evaluation.metrics import generation, retrieval

VERIFIED_CAUSES = {
    **dict.fromkeys(('QU-05', 'QU-06', 'CR-01', 'CR-02', 'CR-05', 'CR-11', 'CR-13',
                     'CR-14', 'CM-04', 'RT-20'),
                    'The checked-out menu recognizer uses a vocabulary that omits these dish terms.'),
    **dict.fromkeys(('QU-11', 'QU-12', 'QU-13', 'QU-14', 'QU-15', 'CM-05', 'CM-17'),
                    'The checked-out query schema and processor have no weather or setting field.'),
}


class EvaluationReport:
    def __init__(self):
        self.rows = []

    def pytest_collectreport(self, report):
        if report.failed:
            self.rows.append({'id': report.nodeid, 'group': 'legacy', 'status': 'failed'})

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        report = (yield).get_result()
        if report.when != 'call' and not (report.when == 'setup' and report.outcome != 'passed'):
            return
        row = dict(getattr(item, 'eval_trace', {'id': item.nodeid, 'group': 'legacy'}))
        reason = None
        if report.skipped and isinstance(report.longrepr, tuple):
            reason = report.longrepr[2]
        row.update(status=report.outcome, reason=reason,
                   failure_type=call.excinfo.typename if report.failed else None)
        self.rows.append(row)


def summarize(rows, reviews):
    groups = {}
    for row in rows:
        groups.setdefault(row['group'], Counter())[row['status']] += 1
    search_rows = [{'predicted': r['retrieved_ids'], 'relevance': {r['expected']['target']: 3}}
                   for r in rows if r['group'] == 'RT' and r['expected']['exhaustive']
                   and isinstance(r['actual'], list) and r['failure_stage'] == 'retrieval']
    constraints = [r for r in rows if r['group'] == 'CR' and r['actual'] is not None]
    final_count = sum(len(r['recommendation_ids']) for r in constraints)
    no_match = [r for r in constraints if not r['expected']['ids']]
    query_rows = [r for r in rows if r['group'] == 'QU' and r['actual'] is not None]
    annotations = [entry['annotations'] for entry in reviews['generation'] if entry['annotations'] is not None]
    naturalness = [a['naturalness'] for a in annotations]
    def accuracy(cases):
        return sum(r['status'] == 'passed' for r in cases) / len(cases) if cases else None
    return {
        'total': len(rows), 'status': Counter(r['status'] for r in rows),
        'groups': groups,
        'priority_failures': Counter(r.get('priority', 'legacy') for r in rows if r['status'] == 'failed'),
        'metrics': {
            'intent_accuracy': accuracy([r for r in query_rows if {'route', 'intent'} & r['expected'].keys()]),
            'entity_accuracy': accuracy([r for r in query_rows if not {'route', 'intent'} & r['expected'].keys()]),
            'exact_target_search_at_5': retrieval(search_rows, k=5),
            'constraint_violation_rate': sum(len(set(r['recommendation_ids']) - set(r['expected']['ids']))
                                             for r in constraints) / final_count if final_count else None,
            'no_match_correctness': accuracy(no_match),
            'generation_human_review': {
                **generation([{'annotations': a} for a in annotations]),
                'naturalness': sum(naturalness) / len(naturalness) if naturalness else None,
            },
        },
        'cases': rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('project/bot/evaluation/reports'))
    parser.add_argument('--split', choices=('development', 'holdout'))
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--legacy', action='store_true', help='Also run the existing suite')
    parser.add_argument('--reviews', type=Path, default=Path('project/bot/evaluation/ground_truth_review.json'))
    args = parser.parse_args()
    os.environ['HANOI_EVAL_LIVE_GEMINI'] = '1' if args.live else '0'
    os.environ.setdefault('HF_HUB_OFFLINE', '1')
    os.environ.setdefault('ANONYMIZED_TELEMETRY', 'False')
    from project.bot.evaluation.test_baseline import CASES

    plugin = EvaluationReport()
    paths = ['project/bot/evaluation/test_baseline.py']
    if args.split:
        paths = [f'{paths[0]}::test_baseline[{c["id"]}]' for c in CASES if c['split'] == args.split]
    if args.legacy:
        paths.append('project/bot/tests')
    code = pytest.main(['-q', '--tb=no', '--show-capture=no', *paths], plugins=[plugin])
    # unittest subtests are reported separately by newer pytest versions.
    by_id = {}
    for row in plugin.rows:
        previous = by_id.get(row['id'])
        if previous is None or previous['status'] != 'failed':
            by_id[row['id']] = row
    rows = list(by_id.values())
    for row in rows:
        constraints = row.get('constraints') or {}
        if row['status'] == 'failed' and 'weather' not in constraints and not constraints.get('hard_constraints'):
            row['root_cause'] = VERIFIED_CAUSES.get(row['id'])
    result = summarize(rows, json.loads(args.reviews.read_text(encoding='utf-8')))
    result['pytest_exit_code'] = int(code)
    result['scope'] = args.split or 'all'
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'baseline.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# Hanoi Explorer AI baseline', '', f"Executed pytest cases: {result['total']}",
             '', '| Group | Passed | Failed | Skipped |', '|---|---:|---:|---:|']
    for group, counts in sorted(result['groups'].items()):
        lines.append(f"| {group} | {counts['passed']} | {counts['failed']} | {counts['skipped']} |")
    lines += ['', '## Priority failures', '',
              ', '.join(f'{level}: {result["priority_failures"][level]}' for level in ('P0', 'P1', 'P2')),
              '', '## Metrics', '', '```json', json.dumps(result['metrics'], indent=2), '```',
              '', '## Failures and skips', '']
    lines += [f"- **{r['id']}** ({r.get('priority', 'legacy')}) {r['status']} · "
              f"{r.get('failure_stage', 'test')} · {r.get('reason') or r.get('input', '')}"
              for r in rows if r['status'] != 'passed']
    lines += ['', 'Only named-target retrieval cases with complete target labels contribute to search metrics.',
              'See [audit, dataset limits and repair priorities](../BASELINE.md) and '
              '[ground-truth review](../ground_truth_review.json).']
    (args.output / 'baseline.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return int(code)


if __name__ == '__main__':
    raise SystemExit(main())
