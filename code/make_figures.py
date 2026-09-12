"""Figures only from executed numerical records and explicit graph specifications."""
from pathlib import Path
import json,sys,textwrap
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
root=Path(__file__).resolve().parents[1];out=root/'results';fd=root/'figures';fd.mkdir(exist_ok=True)
sys.path.insert(0,str(root/'code'))
from model import reference_specs,route,scenario_grid,tree_spec,binary_trees,queue_probe
order=['CDO','MANADO','KURANJI','HUE','KADAMAIAN','HATYAI']
short=['CDO','Manado','Kuranji','Hue\n(lagoon)','Kadamaian','Hat Yai\n(lake)']

def save(fig,name):
 fig.tight_layout();fig.savefig(fd/(name+'.png'),dpi=180,bbox_inches='tight');plt.close(fig)

p=pd.read_csv(out/'paired_timing_summary.csv');a=p[p.storage_tau==0].set_index('case').loc[order]
fig,ax=plt.subplots(figsize=(10,4.8));bars=ax.bar(np.arange(6),a.mean_delta*100)
ax.bar_label(bars,fmt='+%.2f pp',padding=3);ax.set_xticks(range(6),short)
ax.set_ylim(0,16);ax.set_ylabel('Change in mean spilled input (percentage points)')
ax.set_title('Simultaneous source starts increased ensemble-mean spill in all six models\nPaired inputs, capacities and delays; neutral special-storage functions')
save(fig,'01_paired_timing')

c=pd.read_csv(out/'CDO_rewiring_summary.csv');fig,ax=plt.subplots(figsize=(10.5,4.7))
bars=ax.bar(range(15),c.mean_spill*100)
for i,v in enumerate(c.variant):
 if v=='binary_12':bars[i].set_hatch('///')
 if c.iloc[i]['shape']=='balanced':bars[i].set_hatch('..')
ax.set_xticks(range(15),[v.replace('binary_','') for v in c.variant]);ax.set_ylabel('Mean input spilled (%)');ax.set_ylim(0,26)
ax.set_xlabel('Labelled binary arrangement ID; 12 = supplied CDO sequence (hatched)')
ax.set_title('CDO arrangement versus source- and graph-size-matched alternatives\nDotted bars: balanced shape; others: sequential shape. Not 15 independent river sites.')
save(fig,'02_cdo_rewiring')

p=pd.read_csv(out/'summary_all.csv');p=p[(p.experiment=='reference')&p.role.isin(['receiver','urban_and_receiver'])]
fig,ax=plt.subplots(figsize=(9,4.6));x=np.arange(2)
for offset,tau in [(-.26,0.),(0.,2.),(.26,8.)]:
 vals=[float(p[(p.case==site)&(p.storage_tau==tau)].mean_spill_fraction.iloc[0])*100 for site in ['MANADO','HUE']]
 bars=ax.bar(x+offset,vals,width=.25,label=f'Release-time parameter {tau:g}');ax.bar_label(bars,fmt='%.2f%%',padding=3)
ax.set_xticks(x,['Manado receiver','Huong lagoon receiver']);ax.set_ylim(0,29);ax.set_ylabel('Mean input spilled (%)');ax.legend(loc='upper right')
ax.set_title('Keeping connections fixed, changing storage-release functions changes spill\nSynthetic release times; not measured reservoir operating conditions')
save(fig,'03_storage_effect')

k=pd.read_csv(out/'Kuranji_order_summary.csv');fig,ax=plt.subplots(figsize=(9,4.7))
ax.hist(k.mean_spill_fraction*100,bins=12);f=json.loads((out/'computed_findings.json').read_text())['Kuranji']
ax.axvline(f['collapsed_mean_spill']*100,linestyle='--',label='Unresolved single-zone abstraction')
ax.set_xlabel('Mean input spilled (%) over the same 72 scenarios x 12 probe settings')
ax.set_ylabel('Number of labelled refinements');ax.legend();ax.set_title('Unspecified confluence order changes the Kuranji result\n105 hypothetical binary refinements; distribution is NOT a probability distribution')
save(fig,'04_kuranji_uncertainty')

p=pd.read_csv(out/'outlet_counterfactual_summary.csv');fig,ax=plt.subplots(figsize=(9.5,4.7));x=np.arange(3)
conds=['unrestricted','common_50pct','one_route_blocked']
for offset,top,label in [(-.18,'one_route','One route'),(.18,'two_equal_budget_routes','Two routes, same total capacity')]:
 vals=[p[(p.condition==v)&(p.topology==top)].mean_spill_fraction.iloc[0]*100 for v in conds]
 bars=ax.bar(x+offset,vals,width=.35,label=label);ax.bar_label(bars,fmt='%.1f%%',padding=3)
ax.set_xticks(x,['No restriction','Both share 50%\nservice restriction','One route\nfully blocked']);ax.set_ylim(0,108)
ax.set_ylabel('Mean input spilled (%)');ax.legend();ax.set_title('Outlet multiplicity helps against a local failure, not a shared capacity penalty\nHypothetical Hat Yai urban buffer; zero-capacity case retains unspilled water')
save(fig,'05_shared_boundary')

# Executed counterexample: storage retimes one branch into the other.
sp=reference_specs()[1];sc=scenario_grid()[529];fig,ax=plt.subplots(figsize=(9.5,4.5))
for tau in [0.,8.]:
 a,_,_=route(sp,sc,tau);q=a['R'].sum(axis=0)
 ax.plot(np.arange(90),q[:90],label=f'Release-time parameter {tau:g}; spill {100*queue_probe(q,5.,10.)[0]/100:.2f}%')
ax.axhline(5.,linestyle='--',label='Assigned service capacity 5');ax.set_xlabel('Abstract tick (not hours)');ax.set_ylabel('Input units arriving per tick')
ax.set_title('Counterexample: added routing storage can retime arrivals adversely\nManado coarse graph, scenario 529; same total input, capacity 5, buffer 10')
ax.legend();save(fig,'06_counterexample_storage')

# Schematic locations are drawing coordinates only. No coordinates or flood footprints are inferred.
positions={
'CDO':{'U':(0,3),'T':(0,1.8),'J0':(2.3,2.4),'B':(2.3,.7),'J1':(4.6,1.7),'L':(4.6,-.1),'R':(7,1.5),'O':(9.5,1.5)},
'MANADO':{'U':(0,3),'S0':(2.1,3),'S1':(4.2,3),'S2':(6.3,3),'T':(6.3,1.4),'J0':(8.4,2.4),'L':(8.4,.5),'R':(10.6,2),'O':(12.8,2)},
'KURANJI':{'K':(0,4),'B':(0,3),'S':(0,2),'J':(0,1),'M':(0,0),'Z':(3.1,2),'R':(6.2,2),'O':(9.3,2)},
'HUE':{'T':(0,4),'H':(0,2),'B':(0,0),'S0':(2.2,4),'S1':(2.2,2),'S2':(2.2,0),'J0':(4.5,3),'U':(6.8,3),'L':(6.8,0),'J1':(9.1,2),'R':(11.5,2),'O0':(13.9,3.2),'O1':(13.9,.8)},
'KADAMAIAN':{'K':(0,3),'P':(0,1.5),'J0':(3,2.2),'L':(3,0),'R':(6,1.5),'O':(9.3,1.5)},
'HATYAI':{'U':(0,5),'W':(0,4),'A':(0,3),'T':(0,2),'H':(0,1),'L':(0,0),'Urb':(3.3,2.5),'D0':(6.5,4),'D1':(6.5,1),'R':(9.7,2.5),'O':(12.9,2.5)}}
for sp in reference_specs():
 pos=positions[sp.case];fig,ax=plt.subplots(figsize=(13.2,4.8));w=1.8;h=.62
 patches={}
 for n,(x,y) in pos.items():
  box=FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle='round,pad=0.04',fill=False,
       linewidth=1.5 if n in sp.observations.values() else 1.,linestyle='--' if n.startswith('S') and n not in sp.sources else '-')
  ax.add_patch(box);patches[n]=box
  label=sp.names[n]
  ax.text(x,y,'\n'.join(textwrap.wrap(label,20)),ha='center',va='center',fontsize=8.4)
 for u,v,d,f in sp.edges:
  x,y=pos[u];xx,yy=pos[v]
  arrow=FancyArrowPatch((x,y),(xx,yy),patchA=patches[u],patchB=patches[v],arrowstyle='-|>',mutation_scale=10,
     linestyle=':' if sp.case=='KURANJI' or (sp.case=='HUE' and u=='L') else '-',linewidth=.85)
  ax.add_patch(arrow)
 xs=[v[0] for v in pos.values()];ys=[v[1] for v in pos.values()]
 ax.set_xlim(min(xs)-1.2,max(xs)+1.2);ax.set_ylim(min(ys)-.75,max(ys)+.9);ax.axis('off')
 ax.set_title(sp.label+' | report-constrained coarse graph\nDrawing coordinates only. Not a mapped river network or a flood-extent map.',fontsize=13)
 fig.text(.5,.01,'Dashed boxes: named controls. Dotted links: unresolved confluence-zone aggregation or assumed residual entry. Capacities and delays are synthetic.',ha='center',fontsize=8)
 save(fig,'graph_'+sp.case)
(root/'inputs/drawing_positions.json').write_text(json.dumps(positions,indent=2))
print('Saved 12 figures: 6 executed-result charts and 6 explicitly coarse graph schematics.')
