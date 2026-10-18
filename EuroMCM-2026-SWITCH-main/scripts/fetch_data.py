import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
ROUTE_COMMIT = '0b64fdafe049e596a3f5657c219329f24af24198'
GSM_COMMIT = '3101c7d5072418e28b9008a6636bde82a006892c'
SOURCES = {
    'gsm8k_responses.csv': f'https://raw.githubusercontent.com/lm-sys/RouteLLM/{ROUTE_COMMIT}/routellm/evals/gsm8k/gsm8k_responses.csv',
    'generate_responses.py': f'https://raw.githubusercontent.com/lm-sys/RouteLLM/{ROUTE_COMMIT}/routellm/evals/gsm8k/generate_responses.py',
    'test.jsonl': f'https://raw.githubusercontent.com/lm-sys/RouteLLM/{ROUTE_COMMIT}/routellm/evals/gsm8k/test.jsonl',
    'contaminated_prompts.jsonl': f'https://raw.githubusercontent.com/lm-sys/RouteLLM/{ROUTE_COMMIT}/routellm/evals/gsm8k/contaminated_prompts.jsonl',
    'LICENSE': f'https://raw.githubusercontent.com/lm-sys/RouteLLM/{ROUTE_COMMIT}/LICENSE',
    'GSM8K_LICENSE': f'https://raw.githubusercontent.com/openai/grade-school-math/{GSM_COMMIT}/LICENSE',
}

def main():
    raw = ROOT / 'data/raw'
    raw.mkdir(exist_ok=True, parents=True)
    manifest = ROOT / 'data/source_manifest.json'
    expected = {r['file']:r for r in json.loads(manifest.read_text())} if manifest.exists() else {}
    records = []
    for name, url in SOURCES.items():
        path = raw / name
        if not path.exists():
            path.write_bytes(urlopen(url, timeout=60).read())
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if name in expected and expected[name]['url'] == url and digest != expected[name]['sha256']:
            raise RuntimeError('Source hash mismatch: '+name+'; refusing to overwrite the trusted manifest.')
        records.append(dict(file=name, url=url, sha256=digest, bytes=path.stat().st_size))
    manifest.write_text(json.dumps(records, indent=2)+'\n')
    print('Pinned source files available; SHA256 manifest written.')

if __name__ == '__main__':
    main()
