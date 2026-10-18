from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from simulate_switch import effort, probability, Scenario
GEN=ROOT/'paper/generated';GEN.mkdir(exist_ok=True)
FIG=ROOT/'figures';FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':14,'axes.spines.top':False,
                     'axes.spines.right':False,'pdf.fonttype':42,'figure.constrained_layout.use':True})

def table(name,headers,rows,align=None):
    text='\\begin{tabular}{'+(align or 'l'+'r'*(len(headers)-1))+'}\n\\toprule\n'
    text+=' & '.join(headers)+' \\\n\\midrule\n'
    for row in rows:text+=' & '.join(map(str,row))+' \\\n'
    text+='\\bottomrule\n\\end{tabular}\n'
    # Every row must end in two literal backslashes for TeX.
    text=text.replace(' \\\n',' \\\\\n')
    (GEN/(name+'.tex')).write_text(text)

def save(fig,name):
    fig.savefig(FIG/(name+'.pdf'))
    fig.savefig(FIG/(name+'.png'),dpi=180)
    plt.close(fig)

def main():
    sim=pd.read_csv(ROOT/'results/simulation_summary.csv').set_index('policy')
    ben=pd.read_csv(ROOT/'results/benchmark_summary.csv').set_index('policy')
    sen=pd.read_csv(ROOT/'results/sensitivity_summary.csv')
    cat=pd.read_csv(ROOT/'results/category_summary.csv')
    audit=json.loads((ROOT/'results/benchmark_data_audit.json').read_text())
    pair=pd.read_csv(ROOT/'results/paired_differences.csv')
    br=pd.read_csv(ROOT/'results/benchmark_seeds.csv')
    scorer=pd.read_csv(ROOT/'results/benchmark_scorer.csv')
    short={'Always Small':'Always small','Always Large':'Always large','Fixed':'Fixed',
           'Basic router':'Basic','Router + cascade':'+ Cascade','Router + reasoning':'+ Reasoning',
           'SWITCH':'SWITCH','Router + fixed effort':'R fixed effort','Cascade + fixed effort':'R fixed + cascade'}
    policies=list(short)
    rows=[]
    for p in policies:
        r=sim.loc[p]
        rows.append([short[p],f'${100*r.correct_mean:.2f}\\pm{100*r.correct_sd:.2f}$',
                     f'${r.cost_mean:.2f}\\pm{r.cost_sd:.2f}$',f'{r.energy_wh_mean:.2f}',f'{r.carbon_g_mean:.3f}'])
    table('ablation',['Policy','Correct (\\%)','Cost units','Wh','g CO$_2$e'],rows)
    rows=[]
    for p in ['Always Small','Always Large','Basic router','Router + cascade','Random matched calls','Oracle upper bound']:
        r=ben.loc[p]
        label={'Random matched calls':'Random matched','Oracle upper bound':'Oracle bound'}.get(p,short.get(p,p))
        rows.append([label,f'${100*r.correct_mean:.2f}\\pm{100*r.correct_sd:.2f}$',
                     f'${r.cost_mean:.2f}\\pm{r.cost_sd:.2f}$',f'{100*r.strong_share_mean:.1f}'])
    table('benchmark',['Policy','Label accuracy (\\%)','Assumed cost','Strong (\\%)'],rows)
    scenario_labels={
       'performance_shift=-0.08':'Quality curves $-0.08$',
       'performance_shift=0.05':'Quality curves $+0.05$',
       'reasoning_multiplier=0.0':'No reasoning benefit',
       'reasoning_multiplier=0.5':'Half reasoning benefit',
       'reasoning_multiplier=1.5':'1.5 times reasoning benefit',
       'rho=0.0':'Outcome dependence $\\rho=0$',
       'rho=0.9':'Outcome dependence $\\rho=0.9$',
       'confidence_noise=0.25':'25\\% random score',
       'confidence_noise=0.5':'50\\% random score',
       'confidence_noise=1.0':'100\\% random score',
       'confidence_bias=-0.15':'Score bias $-0.15$',
       'confidence_bias=0.15':'Score bias $+0.15$',
       'difficulty_noise=0.06':'Difficulty SD 0.06',
       'difficulty_noise=0.28':'Difficulty SD 0.28',
       'difficulty_noise=0.42':'Difficulty SD 0.42',
       'intensity_scale=0.25':'Grid intensities $\\times0.25$',
       'intensity_scale=2.0':'Grid intensities $\\times2$',
       'load=0.78':'High load 0.78',
       'outage=0.2':'20\\% large-model outages',
       'relocate=True':'Relocation enabled',
       'hard_mix=True':'Harder workload'}
    def sensitivity_table(name,keys,include_delay=False):
        rows=[]
        r=sim.loc['SWITCH']
        rows.append(['Base',f'${100*r.correct_mean:.2f}\\pm{100*r.correct_sd:.2f}$',f'{r.cost_mean:.2f}',f'{r.carbon_g_mean:.3f}']+([f'{r.delay_s_mean:.2f}'] if include_delay else []))
        for key in keys:
            r=sen[(sen.scenario==key)&(sen.policy=='SWITCH')].iloc[0]
            rows.append([scenario_labels[key],f'${100*r.correct_mean:.2f}\\pm{100*r.correct_sd:.2f}$',f'{r.cost_mean:.2f}',f'{r.carbon_g_mean:.3f}']+([f'{r.delay_s_mean:.2f}'] if include_delay else []))
        table(name,['Scenario','Correct (\\%)','Cost','g CO$_2$e']+(['Time (s)'] if include_delay else []),rows)
    sensitivity_table('performance',list(scenario_labels)[:7])
    sensitivity_table('confidence',list(scenario_labels)[7:15])
    sensitivity_table('operations',list(scenario_labels)[15:],include_delay=True)
    rows=[]
    for _,r in cat[cat.policy=='SWITCH'].iterrows():
        rows.append([r.category,f'${100*r.correct_mean:.2f}\\pm{100*r.correct_sd:.2f}$',f'{r.cost_mean:.2f}',f'{100*r.review_mean:.1f}'])
    table('categories',['Category','Correct (\\%)','Cost','Review flag (\\%)'],rows)
    base=pd.read_csv(ROOT/'results/reconstructed_base.csv')
    table('base_seed',['Policy','Correct (\\%)','Cost','g CO$_2$e'],[
        [short[r.policy],f'{100*r.correct:.2f}',f'{r.cost:.2f}',f'{r.carbon_g:.3f}'] for r in base.itertuples() if r.policy in ['Always Small','Always Large','Fixed','SWITCH']])
    values={
      'SimAccuracy':100*sim.loc['SWITCH','correct_mean'],
      'LargeAccuracy':100*sim.loc['Always Large','correct_mean'],
      'SimCost':sim.loc['SWITCH','cost_mean'],
      'SimCarbon':sim.loc['SWITCH','carbon_g_mean'],
      'CostSaving':100*pair.cost_saving.mean(),
      'CarbonSaving':100*pair.carbon_saving.mean(),
      'Rebound':pair.rebound_multiplier.mean(),
      'OverheadLimit':pair.overhead_breakeven.mean(),
      'PairedGain':100*pair.accuracy_difference.mean(),
      'PairedLow':100*pair.accuracy_difference.quantile(.025),
      'PairedHigh':100*pair.accuracy_difference.quantile(.975),
      'ObservedSmall':100*audit['weak_accuracy'],
      'ObservedLarge':100*audit['strong_accuracy'],
      'BenchBasic':100*ben.loc['Basic router','correct_mean'],
      'BenchCascade':100*ben.loc['Router + cascade','correct_mean'],
      'BenchLarge':100*ben.loc['Always Large','correct_mean'],
      'ScorerAuc':scorer.auc.mean(), 'ScorerBrier':scorer.brier.mean(),
      'ConstantBrier':scorer.constant_brier.mean(),
      'EffortClean':float(effort(.55,120)), 'EffortDirty':float(effort(.55,400)),
      'FullLatency':sim.loc['SWITCH','delay_s_mean'],
      'LargeLatency':sim.loc['Always Large','delay_s_mean'],
    }
    for key,val in values.items():values[key]=f'{val:.3f}' if key in ['ScorerAuc','ScorerBrier','ConstantBrier','SimCarbon'] else f'{val:.2f}'
    piv=br.pivot(index='seed',columns='policy',values='correct')
    values.update(BasicMiss=str(int((piv['Basic router']<.95*piv['Always Large']).sum())),
                  CascadeMiss=str(int((piv['Router + cascade']<.95*piv['Always Large']).sum())),
                  BenchN=str(audit['clean_rows']),WeakOnly=str(audit['weak_only']),StrongOnly=str(audit['strong_only']),
                  Neither=str(audit['neither']),Both=str(audit['both_correct']))
    (GEN/'numbers.tex').write_text('\n'.join('\\newcommand{\\'+k+'}{'+v+'}' for k,v in values.items())+'\n')
    (ROOT/'results/paper_numbers.json').write_text(json.dumps(values,indent=2)+'\n')
    # Dot-and-interval plot uses seed SD, not misleading confidence intervals.
    pp=['Basic router','Router + cascade','Router + reasoning','SWITCH']
    fig,ax=plt.subplots(figsize=(6.5,2.8))
    for j,p in enumerate(pp):
        r=sim.loc[p]; ax.errorbar(r.cost_mean,100*r.correct_mean,xerr=r.cost_sd,yerr=100*r.correct_sd,fmt=['o','s','^','D'][j],capsize=4,label=short[p])
        ax.annotate(['Basic','Cascade','Reasoning','SWITCH'][j],(r.cost_mean,100*r.correct_mean),xytext=(5,8),textcoords='offset points',fontsize=13.5)
    ax.axhline(100*sim.loc['Always Large','correct_mean'],color='.4',ls='--')
    ax.text(2.35,91.1,'Always large',fontsize=13.5,color='.3')
    ax.set(xlabel='Assumed cost units per request',ylabel='Synthetic correctness (%)',xlim=(2.3,5.0),ylim=(82,96))
    save(fig,'ablation')
    fig,ax=plt.subplots(figsize=(6.5,3.1))
    pp=['Always Large','Basic router','Router + cascade','Random matched calls']
    for j,p in enumerate(pp):
        r=ben.loc[p];ax.errorbar(100*r.correct_mean,j,xerr=100*r.correct_sd,fmt='o',capsize=4,color='#174b6b')
    ax.set(yticks=range(len(pp)),yticklabels=['Always GPT-4','Basic','Cascade','Random matched'],xlabel='Published-label accuracy (%)',xlim=(70,92))
    ax.invert_yaxis();save(fig,'benchmark')
    fig,ax=plt.subplots(figsize=(6.5,3.5))
    ss=sen[(sen.policy=='SWITCH')&sen.scenario.str.startswith('confidence_noise=')].copy()
    xx=[0]+[float(v.split('=')[1]) for v in ss.scenario]
    yy=[sim.loc['SWITCH','correct_mean']]+ss.correct_mean.tolist()
    sd=[sim.loc['SWITCH','correct_sd']]+ss.correct_sd.tolist()
    ax.errorbar(xx,100*np.array(yy),yerr=100*np.array(sd),fmt='o-',capsize=4,color='#174b6b')
    ax.set(xlabel='Share of random information in score',ylabel='Synthetic correctness (%)',ylim=(85,96));save(fig,'confidence')
    fig,ax=plt.subplots(figsize=(6.5,3.5))
    xx=np.linspace(0,3,250)
    for intensity in [120,400]:
        u=probability(.55,1,xx,Scenario())-(.06+.00006*(intensity-120))*xx
        ax.plot(xx,u,label=f'{intensity} g/kWh');ax.axvline(effort(.55,intensity),ls=':',color='.5')
    ax.set(xlabel='Additional reasoning effort x',ylabel='Assumed quality minus effort cost');ax.legend();save(fig,'effort')
    fig,ax=plt.subplots(figsize=(6.5,3.5))
    names=['Always large','SWITCH','SWITCH moved']
    moved=sen[(sen.scenario=='relocate=True')&(sen.policy=='SWITCH')].iloc[0]
    vals=[sim.loc['Always Large','carbon_g_mean'],sim.loc['SWITCH','carbon_g_mean'],moved.carbon_g_mean]
    sd=[sim.loc['Always Large','carbon_g_sd'],sim.loc['SWITCH','carbon_g_sd'],moved.carbon_g_sd]
    ax.barh(names,vals,xerr=sd,capsize=4,color=['#7c8792','#174b6b','#3d7e76'])
    ax.set(xlabel='Scenario-estimated g CO2e per request',xlim=(0,3));ax.invert_yaxis();save(fig,'carbon')
    print('Generated tables, numeric macros, and five figures from verified result files.')

if __name__=='__main__':main()
