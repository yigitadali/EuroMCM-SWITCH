
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]

def hashes():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT/'results').glob('*'))
            if p.suffix in ['.csv','.json'] and p.name not in ['reproduction_check.json','pdf_check.json']}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    before=hashes()
    env=dict(os.environ,MPLCONFIGDIR=str(ROOT/'.cache/matplotlib'),PYTHONPYCACHEPREFIX=str(ROOT/'.cache/pycache'))
    commands=[['scripts/fetch_data.py'],['simulate_switch.py'],['scripts/benchmark.py'],
              ['-m','unittest','discover','-s','tests','-v'],['scripts/make_assets.py']]
    for cmd in commands:subprocess.run([sys.executable]+cmd,cwd=ROOT,env=env,check=True)
    after=hashes(); changed=[k for k in before if before[k]!=after.get(k)]
    result=dict(verified=args.verify,checked_files=len(before),changed_files=changed,
                status='PASS' if not changed else 'CHANGED',python=sys.version,output_hashes=after)
    (ROOT/'results/reproduction_check.json').write_text(json.dumps(result,indent=2)+'\n')
    if args.verify and changed:raise SystemExit('Numerical outputs differ: '+str(changed))
    print('Reproduction comparison:',result['status'], 'across',len(before),'existing output files')

if __name__=='__main__':main()
