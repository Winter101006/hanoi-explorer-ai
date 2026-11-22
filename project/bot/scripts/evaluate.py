"""Score saved predictions and labels; never fabricate annotations."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from project.bot.evaluation import metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('--k', type=int, default=5)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding='utf-8'))
    result = {'generation': metrics.generation(data.get('generation', [])),
              'conversation': metrics.conversation(data.get('conversation', [])),
              'retrieval': metrics.retrieval(data.get('retrieval', []), args.k),
              'recommendation': metrics.recommendation(data.get('recommendation', []))}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
