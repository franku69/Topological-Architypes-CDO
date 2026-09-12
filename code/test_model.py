"""Numerical and conceptual tests independent of experiment conclusions."""
import json
from pathlib import Path
import numpy as np
from model import *

checks=[]
def check(name,passed,detail=''):
    if not passed: raise AssertionError(name+': '+str(detail))
    checks.append(dict(test=name,passed=True,detail=detail))

specs=reference_specs();ss=scenario_grid()
check('Scenario grid size',len(ss)==1152,len(ss))
check('All source / edge / acyclic checks',all(s.graph() is not None for s in specs))
check('Four-leaf binary family size',len(binary_trees(tuple('ABCD')))==15)
check('Five-leaf binary family size',len(binary_trees(tuple('ABCDE')))==105)
# Independently expected finite-buffer arithmetic: 10 -> serve 4, store 3, spill 3.
q=np.array([10.,0.,0.]);z=queue_probe(q,4.,3.)
check('Exact hand queue arithmetic',np.allclose([z[0],z[1],z[2]],[3.,7.,0.]))
q=np.zeros(20);check('Zero input no spill',queue_probe(q,2.,3.)[0]==0)
q=np.array([2.,10.,3.,0.,0.,0.,0.,0.])
check('Unlimited service no spill',queue_probe(q,1e6,0.)[0]==0.)
check('More service never increases spill',all(queue_probe(q,c,2.)[0]>=queue_probe(q,c+1,2.)[0]-1e-10 for c in range(8)))
check('More buffer never increases spill',all(queue_probe(q,2.,b)[0]>=queue_probe(q,2.,b+1)[0]-1e-10 for b in range(8)))
check('Closed outlet accounts for retained water',np.allclose([queue_probe(np.array([10.,0.]),0.,3.)[0],queue_probe(np.array([10.,0.]),0.,3.)[2]],[7.,3.]))
# Independently compute zero-memory CDO source-to-R hops: U,T=3; B=2; L=1.
s=dict(ss[0]);s.update(duration=2,shape='block',spread=0,weights='equal',activation='all',delay='unit',memory=0.)
a,inp,audit=route(specs[0],s)
expected=np.zeros_like(inp)
for i,d in enumerate([3,3,2,1]):expected[i,d:]=inp[i,:-d]
check('CDO paths independently matched',np.allclose(a['R'],expected))
# Hue MUST exclude Bo and downstream residual from pre-Hue forward flow.
a,_,_=route(specs[3],s)
check('Bo not injected upstream of Hue',float(a['U'][2].sum())==0.)
check('Downstream residual not falsely wholly assigned to Hue',float(a['U'][3].sum())==0.)
check('All four Huong groups reach lagoon',np.allclose(a['R'].sum(axis=1),[25.]*4))
# Same contracted neutral source structure in Manado and Kadamaian.
a,_,_=route(specs[1],s);b,_,_=route(specs[4],s)
check('Neutral-storage two-branch clones match under unit delays',np.allclose(a['R'],b['R']))
# Relabeling the network does not change unit-delay routing.
from copy import deepcopy
sp=deepcopy(specs[0]);mp={n:'renamed_'+n for n in sp.names}
sp.sources=[mp[x] for x in sp.sources];sp.names={mp[k]:v for k,v in sp.names.items()};sp.edges=[(mp[u],mp[v],d,f) for u,v,d,f in sp.edges]
sp.observations={k:mp[v] for k,v in sp.observations.items()}
x,_,_=route(specs[0],s);y,_,_=route(sp,s)
check('Graph relabel invariance, unit delay',np.allclose(x['R'],y[mp['R']]))
# Conservation and horizon check with slowest assigned stores and routing memories.
worst=0.;delta=0.
for sp in specs:
  for sid in [0,19,183,777,1151]:
    a,_,au=route(sp,ss[sid],8.)
    b,_,bu=route(sp,ss[sid],8.,horizon=1024)
    worst=max(worst,au['mass_error'])
    for n in sp.observations.values():
      delta=max(delta,abs(a[n].sum()-b[n].sum()))
check('Routing conservation over stress checks',worst<1e-8,worst)
check('512 vs 1024 horizon sensitivity',delta<1e-7,delta)
# Full node graph water volume does NOT count mass once at every junction.
for sp in specs:
    _,_,au=route(sp,s,8.)
    check('Terminal mass '+sp.case,abs(100.-au['terminal_volume']-au['routing_residual'])<1e-8)
# Independent scalar recursion matches filter definition and residual.
x=np.array([[5.,1.,0.,0.,0.]])
y,rem=filter_release(x,2.)
f=1.-np.exp(-.5);state=0.;expected=[]
for value in x[0]:
    release=f*(state+value);state=state+value-release;expected.append(release)
check('Filter matches independent recurrence',np.allclose(y[0],expected) and abs(rem-state)<1e-10)
# Infinite-ish sustained input eventually loses the transient topology distinction.
one=np.ones((4,HORIZON));cdo=specs[0]
trees=binary_trees(tuple(sorted(cdo.sources)))
t0=tree_spec(cdo,trees[0],'test')
u,_,_=route(cdo,s,custom_injection=one);v,_,_=route(t0,s,custom_injection=one)
check('Steady lossless inflow sums equally',abs(u['R'][:,100].sum()-4.)<1e-10 and abs(v['R'][:,100].sum()-4.)<1e-10)
p=Path(__file__).resolve().parents[1]/'results'/'validation.json';p.parent.mkdir(exist_ok=True)
p.write_text(json.dumps(checks,indent=2))
print('PASS',len(checks),'checks')
