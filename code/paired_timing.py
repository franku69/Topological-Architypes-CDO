"""Additional prespecified-type paired timing contrast.
Changes ONLY source onsets: source amounts, shapes, edge delays and storage are fixed.
The base settings are the spread=24 subset of the archived grid. Hypothesis-neutral:
source-aligned starts need not yield aligned arrivals at a downstream node.
"""
from pathlib import Path
import json, gzip, csv
import numpy as np
import pandas as pd
from model import *
root=Path(__file__).resolve().parents[1];out=root/'results'
rows=[];count=0;maxmass=0.;maxbin=0.
for sp in reference_specs():
 for tau in ([0.,8.] if sp.storage else [0.]):
  for s in scenario_grid():
   if s['spread']!=24:continue
   original,meta=forcing(sp,s)
   aligned=np.zeros_like(original)
   for i,start in enumerate(meta['starts']):
    d=s['duration'];aligned[i,:d]=original[i,start:start+d]
   a,_,auditA=route(sp,s,tau,custom_injection=original)
   b,_,auditB=route(sp,s,tau,custom_injection=aligned)
   maxmass=max(maxmass,auditA['mass_error'],auditB['mass_error']);count+=2
   node=sp.observations['receiver'];qa=a[node].sum(axis=0);qb=b[node].sum(axis=0)
   A=queue_grid(qa,np.array(CAPACITIES),np.array(BUFFERS));B=queue_grid(qb,np.array(CAPACITIES),np.array(BUFFERS))
   for x,y in zip(A,B):
    rows.append(dict(case=sp.case,storage_tau=tau,scenario_id=s['scenario_id'],capacity=x[0],buffer=x[1],
      spill_staggered=x[2]/VOLUME,spill_source_aligned=y[2]/VOLUME,
      delta_aligned_minus_staggered=(y[2]-x[2])/VOLUME,
      SI_staggered=node_metrics(a[node])['synchrony'],SI_aligned=node_metrics(b[node])['synchrony']))
   # queue update invariance when piecewise-constant time bins are split in two.
   if s['rep']==0:
    for q in (qa,qb):
     z=queue_probe(q,5.,10.);zz=queue_probe(np.repeat(q*.5,2),2.5,10.)
     maxbin=max(maxbin,abs(z[0]-zz[0]),abs(z[1]-zz[1]),abs(z[2]-zz[2]))
df=pd.DataFrame(rows);df.to_csv(out/'paired_timing_results.csv.gz',index=False,compression={'method':'gzip','compresslevel':1})
df['higher']=df.delta_aligned_minus_staggered>1e-10;df['lower']=df.delta_aligned_minus_staggered < -1e-10
s=df.groupby(['case','storage_tau']).agg(pairs=('scenario_id','size'),mean_delta=('delta_aligned_minus_staggered','mean'),higher_share=('higher','mean'),lower_share=('lower','mean'),source_aligned_spill=('spill_source_aligned','mean'),staggered_spill=('spill_staggered','mean')).reset_index()
s['tie_share']=1-s.higher_share-s.lower_share;s.to_csv(out/'paired_timing_summary.csv',index=False)
log=dict(additional_routes=count,paired_probe_rows=len(df),additional_queue_evaluations=len(df)*2,
 max_routing_mass_error=maxmass,max_queue_bin_subdivision_error=maxbin,
 note='bin-subdivision check is NOT continuous hydraulic timestep convergence')
(out/'paired_timing_execution.json').write_text(json.dumps(log,indent=2))
print(s.to_string(index=False));print(log)
