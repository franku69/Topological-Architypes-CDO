"""Run all document-based and explicitly hypothetical sensitivity experiments.
Usage: python code/run_experiment.py --output results
No Internet, GIS packages, government records, or external data downloads needed.
"""
from __future__ import annotations
import argparse, csv, gzip, json, time, platform, hashlib, sys
from pathlib import Path
import numpy as np
import pandas as pd
from model import *


def write_json(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf-8')

class Writer:
    def __init__(self,path):
        self.f=gzip.open(path,'wt',newline='',encoding='utf-8',compresslevel=1);self.w=None;self.n=0
    def add(self,row):
        if self.w is None:
            self.w=csv.DictWriter(self.f,fieldnames=list(row));self.w.writeheader()
        self.w.writerow(row);self.n+=1
    def close(self): self.f.close()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='results');args=ap.parse_args()
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    root=out.parent;inpdir=root/'inputs';inpdir.mkdir(exist_ok=True)
    specs=reference_specs();scenarios=scenario_grid()
    manifest=dict(seed=SEED,horizon=HORIZON,volume=VOLUME,capacities=CAPACITIES,buffers=BUFFERS,
      main_scenarios=len(scenarios),time_unit='abstract discrete tick; not hour',
      overflow='standalone finite-buffer diagnostic; NOT spatial inundation',
      comparison='normalized forcing; not calibrated geographic risk ranking',
      uncertain_graphs='Kuranji zone -> all 105 binary refinements; not observed networks',
      area_weighting='supplement only in Kuranji, Hue and Kadamaian; no invented areas elsewhere',
      storage_tau=[0.,2.,8.],storage_tau_status='hypothetical release times, not observed operation',
      source='six user-uploaded reports; no external source verification performed')
    write_json(inpdir/'experiment_config.json',manifest)
    pd.DataFrame(scenarios).to_csv(inpdir/'scenario_grid.csv',index=False)
    for spec in specs:write_json(inpdir/(spec.case+'_graph.json'),spec.export())
    pd.DataFrame([topology_metrics(s) for s in specs]).to_csv(out/'topology_descriptors.csv',index=False)
    qw=Writer(out/'probe_results.csv.gz');rw=Writer(out/'routing_audit.csv.gz');nw=Writer(out/'node_metrics.csv.gz')
    sample=[];graphs=[];counter=0;err_route=0.;err_queue=0.;max_tail=0.;start=time.perf_counter()
    def execute(spec,s,experiment='reference',tau=0.,area=False):
        nonlocal counter,err_route,err_queue,max_tail
        a,inputs,audit=route(spec,s,tau,area)
        key=dict(run_id=counter,experiment=experiment,case=spec.case,variant=spec.variant,
                 scenario_id=s['scenario_id'],storage_tau=tau,area_weights=int(area))
        rw.add(dict(**key,input_volume=audit['input_volume'],terminal_volume=audit['terminal_volume'],
          routing_residual=audit['routing_residual'],mass_error=audit['mass_error'],
          weights=json.dumps(audit['weights']),starts=json.dumps(audit['starts']),active=json.dumps(audit['active'])))
        err_route=max(err_route,audit['mass_error']);max_tail=max(max_tail,abs(audit['routing_residual']))
        # Multiple probes are independent experiments, NEVER summed as network-wide spill.
        for node in dict.fromkeys(spec.observations.values()):
            role='urban_and_receiver' if all(v==node for v in spec.observations.values()) else next(k for k,v in spec.observations.items() if v==node)
            met=node_metrics(a[node]);q=a[node].sum(axis=0)
            nw.add(dict(**key,node=node,role=role,**met))
            grid=queue_grid(q,np.array(CAPACITIES),np.array(BUFFERS))
            for c,b,spill,discharged,residual,maxstore,duration,first in grid:
                error=abs(met['volume']-spill-discharged-residual)
                err_queue=max(err_queue,error)
                qw.add(dict(**key,node=node,role=role,capacity=c,buffer=b,
                   peak=met['peak'],synchrony=met['synchrony'],received_volume=met['volume'],
                   spill=spill,spill_fraction=spill/VOLUME,overflow=int(spill>1.e-8),
                   outflow=discharged,final_storage=residual,max_storage=maxstore,
                   spill_duration=int(duration),first_spill=int(first),mass_error=error))
        # A sparse, reproducible library for the offline HTML viewer.
        if experiment=='reference' and s['weights']=='equal' and s['activation']=='all' and s['delay']=='unit' and s['memory']==0. and s['rep']==0:
            for role,node in spec.observations.items():
                q=a[node].sum(axis=0);stop=max(np.where(q>1.e-10)[0][-1]+10,40) if q.max()>0 else 40
                sample.append(dict(case=spec.case,scenario=s,tau=tau,role=role,node=node,
                   sources=spec.sources,names=[spec.names[x] for x in spec.sources],
                   tagged=np.round(a[node][:,:min(stop,HORIZON)],10).tolist(),input_weights=audit['weights'],
                   starts=audit['starts'],variant=spec.variant))
        counter+=1
        return a,audit
    # 1. Primary common assumptions (all six) and typed-storage sensitivity (two supported cases).
    for spec in specs:
        for s in scenarios:execute(spec,s)
        print('Reference',spec.case,counter,'routes',flush=True)
        if spec.storage:
            for tau in (2.,8.):
                for s in scenarios:execute(spec,s,tau=tau)
            print('Typed storage',spec.case,counter,'routes',flush=True)
    # 2. Published-area weighting, never mistaken for calibrated runoff.
    for spec in specs:
        if spec.areas is not None:
            for s in scenarios:
                if s['weights']=='equal':execute(spec,s,'area_sensitivity',area=True)
    # 3. Full four-source binary rewiring family. Same 4 sources, 3 mergers, 7 edges.
    cdo=specs[0]
    for i,tree in enumerate(binary_trees(tuple(sorted(cdo.sources)))):
        sp=tree_spec(cdo,tree,f'binary_{i:02d}')
        graphs.append(dict(case=sp.case,variant=sp.variant,tree=tree_signature(tree),**{'spec':sp.export()}))
        for s in scenarios:execute(sp,s,'CDO_rewiring')
    print('CDO 15-tree matched family',counter,flush=True)
    # 4. Kadamaian alternative pairing (neutral source structure, equal-size graph budget).
    kad=specs[4]
    for i,tree in enumerate(binary_trees(tuple(sorted(kad.sources)))):
        sp=tree_spec(kad,tree,f'binary_{i:02d}')
        graphs.append(dict(case=sp.case,variant=sp.variant,tree=tree_signature(tree),spec=sp.export()))
        for s in scenarios:execute(sp,s,'Kadamaian_rewiring')
    # 5. Hue branch position and uncertain residual placement. No claim they are real changes.
    hue=specs[3]
    for variant in ['Bo_before_Hue_counterfactual','residual_at_Hue_uncertainty']:
        sp=change_hue(hue,variant);graphs.append(dict(case=sp.case,variant=sp.variant,spec=sp.export()))
        for s in scenarios:execute(sp,s,'Hue_position')
    # 6. Kuranji unresolved order: exhaustive 105 labelled binary refinements, 72 fixed scenarios.
    # Chosen by parameter labels, not by outcomes. Full source activation, memory off, rep 0.
    sub=[s for s in scenarios if s['activation']=='all' and s['memory']==0 and s['rep']==0]
    ku=specs[2]
    assert len(sub)==72
    trees=binary_trees(tuple(sorted(ku.sources)));assert len(trees)==105
    for i,tree in enumerate(trees):
        sp=tree_spec(ku,tree,f'refinement_{i:03d}')
        graphs.append(dict(case=sp.case,variant=sp.variant,tree=tree_signature(tree),spec=sp.export()))
        for s in sub:execute(sp,s,'Kuranji_order_uncertainty')
    print('Kuranji 105 refinements',counter,flush=True)
    # 7. Outlet topology / common-cause experiment at Hat Yai's urban aggregate.
    # Capacity is fixed in total. Two outlets do not secretly receive twice the budget.
    ow=Writer(out/'outlet_counterfactuals.csv.gz');hy=specs[5]
    for s in scenarios:
        a,_,audit=route(hy,s);q=a[hy.observations['urban']].sum(axis=0)
        for condition,mult_single,mult_two in [('unrestricted',1.,1.),('common_50pct',.5,.5),('one_route_blocked',0.,.5)]:
            for topology,mult in [('one_route',mult_single),('two_equal_budget_routes',mult_two)]:
                for i,c in enumerate(CAPACITIES):
                    for b in BUFFERS:
                        z=queue_probe(q,c*mult,b)
                        ow.add(dict(case=hy.case,scenario_id=s['scenario_id'],condition=condition,topology=topology,
                             nominal_total_capacity=c,effective_total_capacity=c*mult,buffer=b,
                             spill=z[0],spill_fraction=z[0]/VOLUME,overflow=int(z[0]>1.e-8),
                             final_storage=z[2],unreleased_fraction=(z[0]+z[2])/VOLUME))
    ow.close();qw.close();rw.close();nw.close()
    write_json(inpdir/'alternative_graphs.json',graphs)
    write_json(out/'viewer_series.json',sample)
    log=dict(completed_routes=counter,probe_evaluations=qw.n,node_metric_rows=nw.n,
      outlet_counterfactual_evaluations=ow.n,max_routing_mass_error=err_route,
      max_queue_mass_error=err_queue,max_routing_terminal_residual=max_tail,
      elapsed_seconds=time.perf_counter()-start,python=sys.version,platform=platform.platform(),
      n_scenarios=len(scenarios),n_reference_cases=len(specs),n_kuranji_refinements=len(trees),n_kuranji_scenarios=len(sub),
      model_status='report-derived coarse topology; synthetic parameters; no hydraulic/spatial validation')
    write_json(out/'execution_log.json',log)
    print(json.dumps(log,indent=2),flush=True)

if __name__=='__main__':main()
