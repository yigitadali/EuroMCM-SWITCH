"""Document-based reconstruction. All outcomes and resource values are SYNTHETIC.

Run from any directory: python simulate_switch.py
No network or model APIs. See docs/METHODS.md for assumptions and deviations.
"""
from dataclasses import dataclass, replace
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.special import ndtr

ROOT = Path(__file__).resolve().parent
CATEGORIES = np.array(['FAQ', 'Summary', 'Quantitative', 'Policy'])
POLICIES = ['Always Small', 'Always Large', 'Fixed', 'Basic router',
            'Router + cascade', 'Router + reasoning', 'SWITCH',
            'Router + fixed effort', 'Cascade + fixed effort']
SEEDS = [int(s.generate_state(1)[0]) for s in np.random.SeedSequence(20261018).spawn(30)]

@dataclass
class Scenario:
    name: str = 'base'
    difficulty_noise: float = .14
    confidence_noise: float = 0.
    confidence_bias: float = 0.
    performance_shift: float = 0.
    reasoning_multiplier: float = 1.
    intensity_scale: float = 1.
    rho: float = .5
    load: float = .35
    outage: float = 0.
    relocate: bool = False
    hard_mix: bool = False

def workload(seed, n, train=False, scenario=Scenario()):
    rng = np.random.default_rng(np.random.SeedSequence([seed, int(train)]))
    mix = [.12, .18, .35, .35] if scenario.hard_mix else [.32, .28, .22, .18]
    cat = np.searchsorted(np.cumsum(mix), rng.random(n))
    d = np.clip(np.array([.18,.40,.67,.83])[cat]+rng.normal(0,.10,n),0,1)
    z = rng.normal(size=n)
    independent = rng.normal(size=(n,3))
    # Gaussian common factor preserves uniform marginals and permits unequal outcomes.
    u = ndtr(np.sqrt(scenario.rho)*z[:,None]+np.sqrt(1-scenario.rho)*independent)
    return dict(cat=cat,d=d,noise=rng.normal(size=n),u=u,
                score_good=rng.beta(6,2,(n,3)), score_bad=rng.beta(2,5,(n,3)),
                score_random=rng.random((n,3)),audit=rng.random(n),
                intensity=np.where(rng.random(n)<.60,400.,120.)*scenario.intensity_scale,
                urgent=rng.random(n)<.60,spare=rng.random(n)<.50,
                unavailable=rng.random(n)<scenario.outage)

def effort(d, intensity):
    c = .06+.00006*(intensity-120)
    return np.clip(np.log(.8*(.07+.30*np.asarray(d))/c)/.8,0,3)

def probability(d, m, x, s):
    p = .94-.48*d
    if m == 1:
        p += s.reasoning_multiplier*(.07+.30*d)*(1-np.exp(-.8*x))
    elif m == 2:
        p = .99-.14*d
    return np.clip(p+s.performance_shift,.01,.995)

def resources(m, x):
    return [(1.,1.,.002),(1+.75*x,1+.90*x,.002+.0013*x),(5.5,4.,.009)][m]

def evaluate(data, training, policy, s):
    cascade = policy in ['Router + cascade','SWITCH','Cascade + fixed effort']
    reasoning = policy in ['Router + reasoning','SWITCH','Router + fixed effort','Cascade + fixed effort']
    optimize = policy in ['Router + reasoning','SWITCH']
    adaptive = policy in POLICIES[3:]
    successes = np.zeros((4,3)); totals = np.zeros((4,3))
    for j in range(len(training['d'])):
        k = training['cat'][j]
        for m in range(3):
            training_dh = np.clip(training['d'][j]+s.difficulty_noise*training['noise'][j],0,1)
            x = effort(training_dh,training['intensity'][j]) if m == 1 and optimize else (1. if m == 1 else 0.)
            successes[k,m] += training['u'][j,m] < probability(training['d'][j],m,x,s)
            totals[k,m] += 1
    n = len(data['d']); records = []
    for i in range(n):
        d = data['d'][i]; cat = data['cat'][i]
        dh = np.clip(d+s.difficulty_noise*data['noise'][i],0,1)
        intensity = data['intensity'][i]
        x = float(effort(dh,intensity)) if optimize else 1.
        review = False
        if policy == 'Always Small': m = 0
        elif policy == 'Always Large': m = 2
        elif policy == 'Fixed': m = 0 if dh<.36 else (1 if dh<.65 else 2)
        else:
            candidates = [0,1,2] if reasoning else [0,2]
            q = [.70*probability(dh,v,x,Scenario())+.30*(successes[cat,v]+1)/(totals[cat,v]+2) for v in candidates]
            feasible = [v for v,a in zip(candidates,q) if a >= (.86 if cat==3 else .80)]
            m = min(feasible,key=lambda v:resources(v,x)[0]) if feasible else 2
            review = not feasible
        if m == 2 and data['unavailable'][i]: m = 1
        moved = s.relocate and intensity>120*s.intensity_scale and not data['urgent'][i] and data['spare'][i]
        dest_intensity = 120*s.intensity_scale if moved else intensity
        cost = .12 if adaptive or policy=='Fixed' else 0.
        delay = .14 if adaptive or policy=='Fixed' else 0.
        energy = .00010 if adaptive or policy=='Fixed' else 0.
        cost += .20*int(moved); delay += .75*int(moved); energy += .00015*int(moved)
        used = []; correct = False
        while True:
            used.append(m)
            correct = data['u'][i,m] < probability(d,m,x,s)
            c,t,e = resources(m,x)
            cost += c; delay += t; energy += e
            score = data['score_good'][i,m] if correct else data['score_bad'][i,m]
            score = np.clip((1-s.confidence_noise)*score+s.confidence_noise*data['score_random'][i,m]+s.confidence_bias,0,1)
            if adaptive and data['audit'][i]<.30:
                successes[cat,m] += int(correct); totals[cat,m] += 1
            if not cascade or score>=.50 or m==2: break
            next_model = 1 if m==0 and reasoning else 2
            if next_model==2 and data['unavailable'][i]: break
            m = next_model
        delay += .35*s.load/(1-s.load)
        records.append(dict(request=i,category=CATEGORIES[cat],correct=int(correct),cost=cost,
                            delay_s=delay,energy_wh=1000*energy,carbon_g=energy*dest_intensity,
                            calls=len(used),cascade=int(len(used)>1),review=int(review),
                            relocated=int(moved),final_model=m,call_path='>'.join(map(str,used)),
                            reasoning_effort=x,destination_intensity=dest_intensity))
    return pd.DataFrame(records)

METRICS = ['correct','cost','delay_s','energy_wh','carbon_g','calls','cascade','review']

def summarize(frame, groups, metrics=METRICS):
    rows=[]
    for key, chunk in frame.groupby(groups,sort=False):
        if not isinstance(key,tuple): key=(key,)
        row = dict(zip(groups,key))
        for col in metrics:
            values=chunk[col].to_numpy()
            row[col+'_mean']=values.mean()
            row[col+'_sd']=values.std(ddof=1)
            row[col+'_p025'],row[col+'_p975']=np.quantile(values,[.025,.975])
        rows.append(row)
    return pd.DataFrame(rows)

def main():
    out=ROOT/'results'; out.mkdir(exist_ok=True)
    (ROOT/'data/synthetic').mkdir(exist_ok=True)
    (out/'seeds.json').write_text(json.dumps(SEEDS,indent=2)+'\n')
    base=Scenario(); all_rows=[]; categories=[]; paired=[]; base_records=[]
    for seed in [20261018]+SEEDS:
        data=workload(seed,1200); train=workload(seed,450,True)
        if seed in SEEDS:
            np.savez_compressed(ROOT/f'data/synthetic/seed_{seed}.npz',**data,
                                **{'train_'+k:v for k,v in train.items()})
        runs={p:evaluate(data,train,p,base) for p in POLICIES}
        for p,frame in runs.items():
            row=dict(seed=seed,policy=p,**frame[METRICS].mean().to_dict())
            if seed==20261018:
                base_records.append(row)
                if p=='SWITCH': frame.to_csv(out/'base_request_results.csv',index=False)
            else:
                all_rows.append(row)
                for cat,g in frame.groupby('category'):
                    categories.append(dict(seed=seed,policy=p,category=cat,n=len(g),**g[METRICS].mean().to_dict()))
        if seed!=20261018:
            full=runs['SWITCH']; large=runs['Always Large']
            paired.append(dict(seed=seed,accuracy_difference=full.correct.mean()-large.correct.mean(),
                               cost_saving=1-full.cost.mean()/large.cost.mean(),
                               carbon_saving=1-full.carbon_g.mean()/large.carbon_g.mean(),
                               rebound_multiplier=large.carbon_g.mean()/full.carbon_g.mean(),
                               overhead_breakeven=large.cost.mean()-(full.cost.mean()-.12)))
    pd.DataFrame(base_records).to_csv(out/'reconstructed_base.csv',index=False)
    claims=pd.read_csv(ROOT/'data/original_claims.csv')
    new=pd.DataFrame(base_records);new['accuracy_pct']=100*new.correct
    claims.merge(new[['policy','accuracy_pct','cost','carbon_g']],on='policy',suffixes=('_old_unverified','_new')).to_csv(out/'original_comparison.csv',index=False)
    seeds=pd.DataFrame(all_rows);seeds.to_csv(out/'simulation_seeds.csv',index=False)
    summarize(seeds,['policy']).to_csv(out/'simulation_summary.csv',index=False)
    cat=pd.DataFrame(categories);cat.to_csv(out/'category_seeds.csv',index=False)
    summarize(cat,['policy','category']).to_csv(out/'category_summary.csv',index=False)
    pd.DataFrame(paired).to_csv(out/'paired_differences.csv',index=False)
    scenarios=[]
    for field,values in [('difficulty_noise',[.06,.28,.42]),('confidence_noise',[.25,.5,1.]),
                         ('confidence_bias',[-.15,.15]),('performance_shift',[-.08,.05]),
                         ('reasoning_multiplier',[0.,.5,1.5]),('intensity_scale',[.25,2.]),
                         ('rho',[0.,.9]),('load',[.78]),('outage',[.2]),('relocate',[True]),('hard_mix',[True])]:
        for value in values: scenarios.append(replace(base,name=f'{field}={value}',**{field:value}))
    scenario_rows=[]
    for s in scenarios:
        for seed in SEEDS:
            data=workload(seed,1200,scenario=s); train=workload(seed,450,True,s)
            for p in ['Always Large','SWITCH']:
                f=evaluate(data,train,p,s)
                scenario_rows.append(dict(scenario=s.name,seed=seed,policy=p,**f[METRICS].mean().to_dict()))
    sensitivity=pd.DataFrame(scenario_rows);sensitivity.to_csv(out/'sensitivity_seeds.csv',index=False)
    summarize(sensitivity,['scenario','policy']).to_csv(out/'sensitivity_summary.csv',index=False)
    config=dict(base=base.__dict__,n_train=450,n_test=1200,seeds=SEEDS,
                score_correct_beta=[6,2],score_incorrect_beta=[2,5],score_cutoff=.5,
                training_labels='all routes, synthetic; upfront cost not included',
                scenarios=[s.__dict__ for s in scenarios])
    (out/'simulation_config.json').write_text(json.dumps(config,indent=2)+'\n')
    print('Reconstruction and 30-seed simulation complete; NOT original reproduction.')
    print(summarize(seeds,['policy'])[['policy','correct_mean','correct_sd','cost_mean','carbon_g_mean']].to_string(index=False))

if __name__=='__main__': main()
