from pathlib import Path
import sys
import re
import json
import hashlib
import numpy as np
import pandas as pd
from scipy.stats import rankdata
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from simulate_switch import SEEDS, summarize

ROOT=Path(__file__).resolve().parents[1]
WEAK='mistralai/Mixtral-8x7B-Instruct-v0.1'
STRONG='gpt-4-1106-preview'

def number(text):
    matches=re.findall(r'[-+]?\d*\.?\d+',str(text).replace(',',''))
    return float(matches[-1]) if matches else np.nan

def prepare():
    df=pd.read_csv(ROOT/'data/raw/gsm8k_responses.csv')
    assert df.prompt.notna().all() and df.prompt.is_unique
    for col in [WEAK,STRONG]:
        assert df[col].notna().all() and set(df[col].unique()) <= {True,False}
    truth=pd.read_json(ROOT/'data/raw/test.jsonl',lines=True)
    assert truth.question.is_unique
    joined=df.merge(truth,left_on='prompt',right_on='question',validate='one_to_one')
    assert len(joined)==len(df)
    contaminated=pd.read_json(ROOT/'data/raw/contaminated_prompts.jsonl',lines=True)
    exclusion=df.prompt.isin(contaminated.eval_prompt)
    # Separate parser sensitivity check, not a new ground truth adjudication.
    parser_audit=[]
    for col in [WEAK,STRONG]:
        parsed=joined[col+'_response'].map(number)
        true=joined.answer.str.split('####').str[-1].map(number)
        disagree=(parsed==true)!=joined[col]
        parser_audit.append(dict(model=col,rows=len(df),disagreements=int(disagree.sum())))
    out=pd.DataFrame(dict(row_id=np.arange(len(df)),
        prompt_sha256=df.prompt.map(lambda t:hashlib.sha256(t.encode()).hexdigest()),
        prompt_words=df.prompt.str.split().str.len(),
        response_words=df[WEAK+'_response'].str.split().str.len(),
        final_marker=df[WEAK+'_response'].str.contains('####',regex=False).astype(int),
        weak_correct=df[WEAK].astype(int),strong_correct=df[STRONG].astype(int),excluded=exclusion))
    out.to_csv(ROOT/'data/processed/benchmark_all.csv',index=False)
    clean=out[~out.excluded].reset_index(drop=True)
    clean.to_csv(ROOT/'data/processed/benchmark.csv',index=False)
    counts=dict(raw_rows=len(df),excluded_rows=int(exclusion.sum()),clean_rows=len(clean),
                weak_accuracy=float(clean.weak_correct.mean()),strong_accuracy=float(clean.strong_correct.mean()),
                both_correct=int(((clean.weak_correct==1)&(clean.strong_correct==1)).sum()),
                weak_only=int(((clean.weak_correct==1)&(clean.strong_correct==0)).sum()),
                strong_only=int(((clean.weak_correct==0)&(clean.strong_correct==1)).sum()),
                neither=int(((clean.weak_correct==0)&(clean.strong_correct==0)).sum()),
                parser_audit=parser_audit)
    (ROOT/'results/benchmark_data_audit.json').write_text(json.dumps(counts,indent=2)+'\n')
    return clean

def fit_scores(train, sample):
    prompt_edges=np.unique(np.quantile(train.prompt_words,[1/3,2/3]))
    response_edges=np.unique(np.quantile(train.response_words,[1/3,2/3]))
    tr_pre=np.searchsorted(prompt_edges,train.prompt_words)
    tr_post=2*np.searchsorted(response_edges,train.response_words)+train.final_marker.to_numpy()
    def lookup(keys, target, newkeys, bins):
        # Five prior observations at the overall training accuracy.
        prior=target.mean()
        scores=np.array([(target[keys==k].sum()+5*prior)/((keys==k).sum()+5) for k in range(bins)])
        return scores[newkeys]
    pre=lookup(tr_pre,train.weak_correct.to_numpy(),np.searchsorted(prompt_edges,sample.prompt_words),3)
    post=lookup(tr_post,train.weak_correct.to_numpy(),2*np.searchsorted(response_edges,sample.response_words)+sample.final_marker.to_numpy(),6)
    return pre,post

def route(df,pre,post,tpre,tpost=None):
    initial=pre<tpre
    escalation=(~initial)&(post<tpost) if tpost is not None else np.zeros(len(df),dtype=bool)
    strong=initial|escalation
    y=np.where(strong,df.strong_correct,df.weak_correct)
    cost=np.where(initial,5.5,1.)+5.5*escalation+.12
    return y,cost,strong,escalation,initial

def select(val,pre,post,cascade):
    target=.95*val.strong_correct.mean()
    candidates=[]
    # Candidate breakpoints depend on training-derived score values, not test labels.
    tp=np.r_[0,np.unique(pre)+1e-8,1.01]
    ts=np.r_[0,np.unique(post)+1e-8,1.01] if cascade else [None]
    for a in tp:
        for b in ts:
            y,c,*_=route(val,pre,post,a,b)
            if y.mean()>=target: candidates.append((c.mean(),-y.mean(),a,b))
    assert candidates
    best=min(candidates,key=lambda x:(x[0],x[1],x[2],-1 if x[3] is None else x[3]))
    return best[2],best[3],target

def main():
    data=prepare(); rows=[]; splits=[]; predictions=[]; calibration=[]
    for seed in SEEDS:
        rng=np.random.default_rng(seed); idx=rng.permutation(len(data))
        a=int(.60*len(data)); b=int(.80*len(data))
        tr,va,te=[data.iloc[i].reset_index(drop=True) for i in [idx[:a],idx[a:b],idx[b:]]]
        for label,part in [('train',tr),('validation',va),('test',te)]:
            splits.extend(dict(seed=seed,row_id=int(j),split=label) for j in part.row_id)
        vp,vs=fit_scores(tr,va); tp,ts=fit_scores(tr,te)
        result={}; thresholds={}
        for name,cascade in [('Basic router',False),('Router + cascade',True)]:
            aa,bb,target=select(va,vp,vs,cascade)
            result[name]=route(te,tp,ts,aa,bb)
            thresholds[name]=dict(pre=aa,post=bb,target=target)
        n=len(te); zero=np.zeros(n,dtype=bool); one=np.ones(n,dtype=bool)
        result['Always Small']=(te.weak_correct.to_numpy(),np.ones(n),zero,zero,zero)
        result['Always Large']=(te.strong_correct.to_numpy(),np.full(n,5.5),one,zero,one)
        k=int(result['Basic router'][2].sum())
        chosen=np.zeros(n,dtype=bool); chosen[rng.permutation(n)[:k]]=True
        result['Random matched calls']=(np.where(chosen,te.strong_correct,te.weak_correct),1+4.5*chosen+.12,chosen,zero,chosen)
        # Label-aware comparator, NEVER a deployable routing rule.
        order=np.argsort(-(te.strong_correct-te.weak_correct).to_numpy(),kind='stable')
        oracle=np.zeros(n,dtype=bool); beneficial=order[(te.strong_correct-te.weak_correct).to_numpy()[order]>0]
        oracle[beneficial[:k]]=True
        result['Oracle upper bound']=(np.where(oracle,te.strong_correct,te.weak_correct),1+4.5*oracle+.12,oracle,zero,oracle)
        y=te.weak_correct.to_numpy(); positive=y==1; ranks=rankdata(ts)
        auc=(ranks[positive].sum()-positive.sum()*(positive.sum()+1)/2)/(positive.sum()*(~positive).sum())
        calibration.append(dict(seed=seed,brier=float(np.mean((ts-y)**2)),auc=float(auc),
                                constant_brier=float(np.mean((tr.weak_correct.mean()-y)**2))))
        for name,(y,c,st,esc,initial) in result.items():
            rows.append(dict(seed=seed,policy=name,n_test=n,correct=y.mean(),cost=c.mean(),strong_share=st.mean(),cascade=esc.mean(),
                             val_target=thresholds.get(name,{}).get('target',np.nan),
                             pre_threshold=thresholds.get(name,{}).get('pre',np.nan),
                             post_threshold=thresholds.get(name,{}).get('post',np.nan)))
            for j in range(n):
                predictions.append(dict(seed=seed,policy=name,row_id=int(te.row_id.iloc[j]),correct=int(y[j]),
                                        cost=c[j],strong=int(st[j]),cascade=int(esc[j])))
    seeds=pd.DataFrame(rows);seeds.to_csv(ROOT/'results/benchmark_seeds.csv',index=False)
    summarize(seeds,['policy'],['correct','cost','strong_share','cascade']).to_csv(ROOT/'results/benchmark_summary.csv',index=False)
    pd.DataFrame(splits).to_csv(ROOT/'results/benchmark_splits.csv',index=False)
    pd.DataFrame(predictions).to_csv(ROOT/'results/benchmark_predictions.csv',index=False)
    pd.DataFrame(calibration).to_csv(ROOT/'results/benchmark_scorer.csv',index=False)
    print('Observed-response replay complete. Splits overlap across seeds; no new model calls.')
    print(seeds.groupby('policy')[['correct','cost','strong_share']].mean().to_string())

if __name__=='__main__':main()
