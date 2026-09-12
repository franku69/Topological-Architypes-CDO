"""Summarize executed records without substituting assumptions for measurements."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from model import *

root=Path(__file__).resolve().parents[1];out=root/'results'
p=pd.read_csv(out/'probe_results.csv.gz')
n=pd.read_csv(out/'node_metrics.csv.gz')
r=pd.read_csv(out/'routing_audit.csv.gz')
s=pd.read_csv(root/'inputs/scenario_grid.csv')
p=p.merge(s,on='scenario_id',how='left',validate='many_to_one')
n=n.merge(s,on='scenario_id',how='left',validate='many_to_one')
keys=['experiment','case','variant','storage_tau','area_weights','role']
summary=p.groupby(keys,sort=False).agg(evaluations=('overflow','size'),overflow_share=('overflow','mean'),mean_spill_fraction=('spill_fraction','mean'),median_spill_fraction=('spill_fraction','median'),max_spill_fraction=('spill_fraction','max')).reset_index()
summary.to_csv(out/'summary_all.csv',index=False)
main=summary[(summary.experiment=='reference')&(summary.storage_tau==0)]
main.to_csv(out/'summary_primary.csv',index=False)
strata=p[p.experiment=='reference'].groupby(['case','storage_tau','role','spread','duration','memory']).agg(mean_spill_fraction=('spill_fraction','mean'),overflow_share=('overflow','mean')).reset_index()
strata.to_csv(out/'summary_strata.csv',index=False)
key=['scenario_id','node','capacity','buffer']
# CDO reference identity and comparison with every labelled binary arrangement.
base=p[(p.experiment=='reference')&(p.case=='CDO')&(p.storage_tau==0)]
cf=p[p.experiment=='CDO_rewiring'].merge(base[key+['spill_fraction','overflow']],on=key,suffixes=('','_base'),validate='many_to_one')
cf['delta_spill']=cf.spill_fraction-cf.spill_fraction_base
cf['greater']=cf.delta_spill>1e-10;cf['less']=cf.delta_spill < -1e-10;cf['tie']=~(cf.greater|cf.less)
alt=json.loads((root/'inputs/alternative_graphs.json').read_text())
lookup={x['variant']:x for x in alt if x['case']=='CDO'}
orig=set(reference_specs()[0].edges)
refid=[v for v,x in lookup.items() if set(tuple(y) for y in x['spec']['edges'])==orig]
assert len(refid)==1
assert np.max(abs(cf.loc[cf.variant==refid[0],'delta_spill']))<1e-10

def shape(t):
 if isinstance(t,str):return '*'
 return '('+','.join(sorted([shape(t[0]),shape(t[1])]))+')'
trees=binary_trees(tuple(sorted(reference_specs()[0].sources)))
labels={f'binary_{i:02d}':('balanced' if not isinstance(t[0],str) and not isinstance(t[1],str) and all(isinstance(x,str) for x in t[0]+t[1]) else 'sequential') for i,t in enumerate(trees)}
cf['shape']=cf.variant.map(labels)
bycf=cf.groupby(['variant','shape']).agg(mean_delta_spill=('delta_spill','mean'),greater_share=('greater','mean'),less_share=('less','mean'),tie_share=('tie','mean'),mean_spill=('spill_fraction','mean')).reset_index()
bycf['tree']=bycf.variant.map({k:v['tree'] for k,v in lookup.items()})
bycf.to_csv(out/'CDO_rewiring_summary.csv',index=False)
cf.groupby(['shape','spread','duration']).agg(mean_spill=('spill_fraction','mean'),mean_delta_spill=('delta_spill','mean')).reset_index().to_csv(out/'CDO_shape_strata.csv',index=False)
# Rank of supplied CDO labelled arrangement among 15. Average ties; 1 = least spill.
ranked=cf.assign(rank=cf.groupby(key).spill_fraction.rank(method='average',ascending=True))
ranked['response_range']=ranked.groupby(key).spill_fraction.transform('max')-ranked.groupby(key).spill_fraction.transform('min')
ranks=ranked[ranked.variant==refid[0]]
informative=ranks[ranks.response_range>1e-10]
rank_info=dict(reference_variant=refid[0],mean_rank=float(ranks['rank'].mean()),median_rank=float(ranks['rank'].median()),
 median_reference_spill=float(base.spill_fraction.median()),mean_reference_spill=float(base.spill_fraction.mean()),
 informative_settings=int(len(informative)),total_settings=int(len(ranks)),mean_informative_rank=float(informative['rank'].mean()),median_informative_rank=float(informative['rank'].median()),rank_of_ensemble_mean=float(bycf.mean_spill.rank().loc[bycf.variant==refid[0]].iloc[0]),
 n_arrangements=15,n_unlabelled_shapes=len(set(shape(t) for t in trees)),
 mean_balanced_delta=float(cf.loc[cf['shape']=='balanced','delta_spill'].mean()),
 balanced_greater=float(cf.loc[cf['shape']=='balanced','greater'].mean()),balanced_less=float(cf.loc[cf['shape']=='balanced','less'].mean()),
 balanced_tie=float(cf.loc[cf['shape']=='balanced','tie'].mean()))
# Storage paired effects: capacity, input and delays are identical, only release time changes.
st=p[(p.experiment=='reference')&(p.storage_tau>0)]
be=p[(p.experiment=='reference')&(p.storage_tau==0)]
st=st.merge(be[['case']+key+['spill_fraction','overflow']],on=['case']+key,suffixes=('','_base'),validate='many_to_one')
st['delta_spill']=st.spill_fraction-st.spill_fraction_base
st['higher']=st.delta_spill>1e-10;st['lower']=st.delta_spill < -1e-10
storage=st.groupby(['case','storage_tau','role']).agg(mean_delta=('delta_spill','mean'),higher_share=('higher','mean'),lower_share=('lower','mean'),mean_spill=('spill_fraction','mean')).reset_index()
storage.to_csv(out/'storage_paired.csv',index=False)
# Area weighting vs equal-source runs, exact matching.
w=p[p.experiment=='area_sensitivity'].merge(be[['case']+key+['spill_fraction']],on=['case']+key,suffixes=('','_base'),validate='many_to_one')
w['delta_spill']=w.spill_fraction-w.spill_fraction_base
w.groupby(['case','role']).agg(mean_delta=('delta_spill','mean'),mean_spill=('spill_fraction','mean')).reset_index().to_csv(out/'area_weight_paired.csv',index=False)
# Bo-location and residual-location intervention.
h=p[p.experiment=='Hue_position'].merge(be[be.case=='HUE'][key+['spill_fraction','received_volume','peak']],on=key,suffixes=('','_base'),validate='many_to_one')
h['delta_spill']=h.spill_fraction-h.spill_fraction_base;h['delta_volume']=h.received_volume-h.received_volume_base
h.groupby(['variant','role']).agg(mean_delta_spill=('delta_spill','mean'),mean_volume_change=('delta_volume','mean'),mean_spill=('spill_fraction','mean')).reset_index().to_csv(out/'Hue_position_paired.csv',index=False)
# Kuranji uncertainty range is a range over alternatives, NOT a confidence interval.
k=p[p.experiment=='Kuranji_order_uncertainty']
ks=k.groupby('variant').agg(mean_spill_fraction=('spill_fraction','mean'),overflow_share=('overflow','mean'),mean_peak=('peak','mean')).reset_index()
ks.to_csv(out/'Kuranji_order_summary.csv',index=False)
ksel=set(k.scenario_id)
kb=be[(be.case=='KURANJI')&(be.scenario_id.isin(ksel))]
ku=dict(n_refinements=ks.shape[0],n_unlabelled_shapes=len(set(shape(t) for t in binary_trees(tuple(sorted(reference_specs()[2].sources))))),
 n_scenarios=len(ksel),collapsed_mean_spill=float(kb.spill_fraction.mean()),
 refinement_min_mean_spill=float(ks.mean_spill_fraction.min()),refinement_max_mean_spill=float(ks.mean_spill_fraction.max()),
 refinement_median_mean_spill=float(ks.mean_spill_fraction.median()),
 min_overflow_share=float(ks.overflow_share.min()),max_overflow_share=float(ks.overflow_share.max()))
# Counterexamples to simple timing/storage or single-pattern universality, retain IDs.
for df,name in [(st,'storage'),(cf[cf['shape']=='balanced'],'CDO_balanced')]:
 for sign,rows in [('increase',df.nlargest(5,'delta_spill')),('decrease',df.nsmallest(5,'delta_spill'))]:
  cols=[c for c in ['case','variant','scenario_id','node','role','storage_tau','capacity','buffer','spill_fraction','spill_fraction_base','delta_spill','spread','duration','weights','activation','delay','memory','rep'] if c in rows]
  rows[cols].to_csv(out/f'counterexamples_{name}_{sign}.csv',index=False)
# Pure graph shared-cut property for Hat Yai aggregate.
g=reference_specs()[5].graph()
cut_to_lake=len(nx.minimum_edge_cut(g,'Urb','R'))
cut_to_gulf=len(nx.minimum_edge_cut(g,'Urb','O'))
# Two outlets equal total budget have identical unrestricted/common-condition outputs.
o=pd.read_csv(out/'outlet_counterfactuals.csv.gz')
os=o.groupby(['condition','topology']).agg(evaluations=('overflow','size'),overflow_share=('overflow','mean'),mean_spill_fraction=('spill_fraction','mean'),mean_unreleased_fraction=('unreleased_fraction','mean')).reset_index()
os.to_csv(out/'outlet_counterfactual_summary.csv',index=False)
a=o[o.topology=='one_route'];b=o[o.topology=='two_equal_budget_routes']
okeys=['scenario_id','condition','nominal_total_capacity','buffer']
cmp=a.merge(b,on=okeys,suffixes=('_one','_two'),validate='one_to_one')
null_delta=float(abs(cmp.loc[cmp.condition.isin(['unrestricted','common_50pct']),'spill_fraction_one']-cmp.loc[cmp.condition.isin(['unrestricted','common_50pct']),'spill_fraction_two']).max())
assert null_delta==0.
# Timing contrast is descriptive (scenario seeds differ); not represented as a paired intervention.
time_summary=be.groupby(['case','role','spread']).agg(mean_spill_fraction=('spill_fraction','mean'),overflow_share=('overflow','mean'),mean_SI=('synchrony','mean')).reset_index()
time_summary.to_csv(out/'timing_summary.csv',index=False)
# Record end-to-end QC, including finite-horizon closeout and area partition sums.
checks=dict(routing_rows=len(r),probe_rows=len(p),max_routing_error=float(r.mass_error.max()),max_probe_error=float(p.mass_error.max()),
 max_probe_final_storage=float(p.final_storage.max()),max_residual=float(abs(r.routing_residual).max()),
 no_negative_spill=bool((p.spill>=-1e-10).all()),no_missing_parameters=bool(p.duration.notna().all()),
 CDO_identity_max_error=float(abs(cf.loc[cf.variant==refid[0],'delta_spill']).max()),outlet_null_max_error=null_delta,
 unique_case_count_reference=int(be.case.nunique()),primary_receiver_evaluations=int(be[be.role.isin(['receiver','urban_and_receiver'])].shape[0]))
findings=dict(CDO=rank_info,Kuranji=ku,HatYai=dict(edge_cut_city_to_lake=cut_to_lake,edge_cut_city_to_gulf=cut_to_gulf),checks=checks)
(out/'computed_findings.json').write_text(json.dumps(findings,indent=2))
print('PRIMARY\n',main.to_string(index=False))
print('\nCDO',json.dumps(rank_info,indent=2))
print('\nSTORAGE\n',storage.to_string(index=False))
print('\nKURANJI',json.dumps(ku,indent=2))
print('\nHUE\n',pd.read_csv(out/'Hue_position_paired.csv').to_string(index=False))
print('\nOUTLETS\n',os.to_string(index=False))
print('\nCOUNTEREXAMPLE STORAGE\n',st.nlargest(1,'delta_spill')[['case','scenario_id','node','capacity','buffer','spill_fraction','spill_fraction_base','delta_spill']].to_string(index=False))
print('\nCHECKS',checks)
