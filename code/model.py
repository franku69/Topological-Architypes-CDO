"""Document-constrained coarse river graph stress experiment.

NOT a hydraulic or geographic inundation model. The six supplied reports constrain
named connections; event inputs, link delays, release times and capacities are
explicit dimensionless assumptions. Unknown minor tributaries are not invented.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from functools import lru_cache
from itertools import product
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import networkx as nx
from scipy.signal import lfilter
from numba import njit

SEED = 260911
VOLUME = 100.0
HORIZON = 512
CAPACITIES = (2., 5., 10., 20.)
BUFFERS = (0., 10., 30.)

@dataclass
class Spec:
    case: str
    label: str
    variant: str
    sources: list[str]
    names: dict[str, str]
    # (upstream, downstream, logical-delay flag, split fraction)
    edges: list[tuple[str, str, int, float]]
    observations: dict[str, str]
    storage: dict[str, float]
    provenance: str
    limitations: str
    areas: list[float] | None = None

    def graph(self) -> nx.DiGraph:
        g = nx.DiGraph()
        g.add_nodes_from(self.names)
        g.add_edges_from((u, v) for u, v, _, _ in self.edges)
        if not nx.is_directed_acyclic_graph(g):
            raise ValueError(f'{self.case}: cycle in directed routing graph')
        if set(n for n in g if g.in_degree(n) == 0) != set(self.sources):
            raise ValueError(f'{self.case}: source set does not match graph')
        for n in g:
            weights = sum(f for u, v, d, f in self.edges if u == n)
            if g.out_degree(n) and abs(weights - 1.) > 1.e-12:
                raise ValueError(f'{self.case}: outgoing fractions at {n} sum to {weights}')
        return g

    def export(self) -> dict:
        return asdict(self)


def e(u: str, v: str, d: int = 1, f: float = 1.) -> tuple:
    return (u, v, d, f)


def reference_specs() -> list[Spec]:
    return [
      Spec('CDO','CDO river corridor','report_coarse', ['U','T','B','L'],
        {'U':'Upper CDO','T':'Tumalaong','B':'Bubunawan','L':'Connected lower laterals',
         'J0':'Tumalaong junction','J1':'Bubunawan junction','R':'Lower CDO receiving corridor','O':'Macajalar Bay boundary'},
        [e('U','J0'),e('T','J0'),e('J0','J1'),e('B','J1'),e('J1','R'),e('L','R'),e('R','O')],
        {'urban':'R','receiver':'R'}, {},
        'CDO report pp. 2-3, 11-12: named confluence order and independent B1-B4 sources.',
        'B4 is a coarse connected-lateral aggregate. Minor topology and branch areas are absent. R is NOT a demonstrated Lapasan inundation node. No Lapasan edge is inferred from proximity.'),
      Spec('MANADO','Tondano-Tikala / Manado','report_coarse',['U','T','L'],
        {'U':'Upper Tondano / lake inflow','T':'Tikala','L':'Lower connected laterals',
         'S0':'Lake Tondano control','S1':'Hydropower control','S2':'Kuwil-Kawangkoan control',
         'J0':'Tondano-Tikala junction','R':'Lower Manado receiver','O':'Manado Bay boundary'},
        [e('U','S0',0),e('S0','S1',0),e('S1','S2',0),e('S2','J0'),e('T','J0'),e('J0','R'),e('L','R'),e('R','O')],
        {'urban':'R','receiver':'R'},{'S0':1.,'S2':.5},
        'Manado report pp. 3, 5, 12, 19: separate mainstem/Tikala, conceptual control sequence and topology metrics.',
        'Controls are functional aggregates, not surveyed chainage. Zero-delay connector edges avoid adding travel merely because a storage box was drawn. Hydropower operation is not simulated. Release times are hypothetical.'),
      Spec('KURANJI','Batang Kuranji / Padang','report_coarse',['K','B','S','J','M'],
        {'K':'Kuranji base','B':'Belimbing','S':'Sungkai','J':'Janiah / Karuah','M':'Limau Manih',
         'Z':'Unresolved middle confluence ZONE','R':'Lower Kuranji receiver','O':'Indian Ocean boundary'},
        [e(x,'Z') for x in ['K','B','S','J','M']]+[e('Z','R'),e('R','O')],
        {'urban':'R','receiver':'R'}, {},
        'Kuranji report pp. 1-3, 7, 13, 21: five-subbasin partition and conceptual confluence network.',
        'Z is NOT a verified five-way point junction. The report does not give the complete order of the five branches. All 105 binary refinements are separately tested as uncertainty alternatives. No extra urban source is added to a partition already totaling 202.69 km2.',
        [19.86,62.64,6.,82.26,31.93]),
      Spec('HUE','Huong / Hue','report_coarse',['T','H','B','L'],
        {'T':'Ta Trach','H':'Huu Trach','B':'Bo','L':'Downstream residual runoff',
         'S0':'Ta Trach reservoir','S1':'Binh Dien reservoir','S2':'Huong Dien reservoir',
         'J0':'Tuan confluence','U':'Hue / Kim Long','J1':'Sinh confluence',
         'R':'Lagoon receiving aggregate','O0':'Thuan An inlet boundary','O1':'Tu Hien inlet boundary'},
        [e('T','S0',0),e('H','S1',0),e('B','S2',0),e('S0','J0'),e('S1','J0'),e('J0','U'),e('U','J1'),
         e('S2','J1'),e('L','J1'),e('J1','R'),e('R','O0',1,.5),e('R','O1',1,.5)],
        {'urban':'U','receiver':'R'}, {'S0':1.,'S1':1.,'S2':1.},
        'Huong report pp. 3, 6, 10-12, 22: Tuan-Hue-Sinh sequence, three control nodes, lagoon/inlet system.',
        'Bo is NEVER added upstream of Hue in the reference. The residual floodplain source is provisionally injected at Sinh, not assigned wholly to Hue; an alternative location is tested. Lagoon/distributaries are aggregated, and 50:50 inlet splitting is assumed, not measured. No reverse/backwater propagation is modeled.',
        [729.,718.,938.,445.]),
      Spec('KADAMAIAN','Kadamaian-Panataran / Kota Belud','report_coarse',['K','P','L'],
        {'K':'Upper Kadamaian','P':'Panataran','L':'Lower / intermediate residual',
         'J0':'Kadamaian-Panataran junction','R':'Tamu Darat / lower receiving aggregate','O':'Coastal receiving boundary aggregate'},
        [e('K','J0'),e('P','J0'),e('J0','R'),e('L','R'),e('R','O')],
        {'urban':'R','receiver':'R'}, {},
        'Kadamaian-Panataran report pp. 2-3, 7, 11: two inlet branches plus residual 108.28 km2.',
        'The extended lowland network is unresolved. A single O is a boundary aggregate, NOT evidence of only one actual coastal route. Sediment-generated active threads are not reconstructed.',
        [155.18,95.90,108.28]),
      Spec('HATYAI','U-Tapao-Khlong Wat / Hat Yai','report_coarse',['U','W','A','T','H','L'],
        {'U':'Upper U-Tapao / Sadao','W':'Khlong Wat','A':'Khlong Wa','T':'Khlong Tam','H':'Khao Kho Hong','L':'Urban direct input',
         'Urb':'Hat Yai entry / storage ZONE','D0':'U-Tapao lakeward path','D1':'Ror.1 path','R':'Songkhla receiving aggregate','O':'Gulf boundary aggregate'},
        [e(x,'Urb') for x in ['U','W','A','T','H','L']]+[e('Urb','D0',1,.5),e('Urb','D1',1,.5),e('D0','R'),e('D1','R'),e('R','O')],
        {'urban':'Urb','receiver':'R'}, {},
        'Hat Yai report pp. 3, 10, 21, 24-26: distinct inputs, two principal lakeward corridors and common receiving lake.',
        'Urb is a shared floodplain entry aggregate, not a claim that six streams meet at a single point. Canal split 50:50 is a neutral assumption. Lake restriction is represented only as receiving-service sensitivity, not a solved water level or backwater field.')
    ]


def scenario_grid() -> list[dict]:
    rows=[]
    for duration,shape,spread,weights,activation,delay,memory,rep in product(
        [2,8,24],['block','triangle'],[0,8,24],['equal','random'],['all','subset'],['unit','heterogeneous'],[0.,2.],range(4)):
        rows.append(dict(scenario_id=len(rows),duration=duration,shape=shape,spread=spread,
            weights=weights,activation=activation,delay=delay,memory=memory,rep=rep))
    return rows


def forcing(spec:Spec, s:dict, horizon:int=HORIZON, area_weights:bool=False) -> tuple[np.ndarray,dict]:
    n=len(spec.sources)
    rng=np.random.default_rng(SEED + int(s['scenario_id'])*104729)
    raw=rng.lognormal(0.,.8,6)[:n]
    scores=rng.random(6)[:n]
    onset_uniform=rng.random(6)[:n]
    if area_weights:
        if spec.areas is None: raise ValueError('No source-consistent areas for '+spec.case)
        w=np.asarray(spec.areas,dtype=float)
    else:
        w=np.ones(n) if s['weights']=='equal' else raw
    active=np.ones(n,dtype=bool)
    if s['activation']=='subset':
        active[:]=False
        active[np.argsort(scores)[-max(1, math.ceil(.6*n)):]]=True
    w=w*active
    w=w/w.sum()
    starts=np.floor(onset_uniform*(s['spread']+1)).astype(int)
    d=int(s['duration'])
    pulse=np.ones(d) if s['shape']=='block' else 1.-abs(2.*(np.arange(d)+.5)/d-1.)
    pulse/=pulse.sum()
    inp=np.zeros((n,horizon),dtype=float)
    for i in range(n): inp[i,starts[i]:starts[i]+d]=VOLUME*w[i]*pulse
    return inp,{'weights':w.tolist(),'starts':starts.tolist(),'active':active.astype(int).tolist()}


def delay_of(key:str,s:dict)->int:
    if s['delay']=='unit': return 1
    # Stable under reruns and rewiring; keyed by edge origin, not Python's hash().
    digest=hashlib.sha256(f"{SEED}|{s['scenario_id']}|{key}".encode()).digest()
    return 1+int.from_bytes(digest[:4],'little')%4


def filter_release(a:np.ndarray,tau:float)->tuple[np.ndarray,float]:
    if tau<=0.: return a.copy(),0.
    f=-math.expm1(-1./tau)
    out=lfilter([f],[1.,-(1.-f)],a,axis=-1)
    residual=float(a.sum()-out.sum())
    return out,residual


def route(spec:Spec,s:dict,storage_tau:float=0.,area_weights:bool=False,
          horizon:int=HORIZON,custom_injection:np.ndarray|None=None)->tuple[dict,np.ndarray,dict]:
    g=spec.graph()
    inp,meta=forcing(spec,s,horizon,area_weights)
    if custom_injection is not None:
        inp=np.asarray(custom_injection,dtype=float)
        if inp.shape!=(len(spec.sources),horizon): raise ValueError('Invalid injection shape')
    a={n:np.zeros_like(inp) for n in g}
    for i,n in enumerate(spec.sources): a[n][i]=inp[i]
    residual=0.
    for n in nx.topological_sort(g):
        out,rem=filter_release(a[n], storage_tau*spec.storage.get(n,0.))
        residual+=rem
        for u,v,logical,frac in spec.edges:
            if u!=n: continue
            x=out*frac
            if logical:
                x,rem=filter_release(x,s['memory'])
                residual+=rem
                # control-chain terminal uses U-like key in neutral clones
                key= {'S2':'U'}.get(n,n) if spec.case=='MANADO' else n
                delay=delay_of(key,s)
                shifted=np.zeros_like(x)
                shifted[:,delay:]=x[:,:-delay]
                residual+=float(x[:,-delay:].sum())
                x=shifted
            a[v]+=x
    terminals=[n for n in g if g.out_degree(n)==0]
    discharged=sum(float(a[n].sum()) for n in terminals)
    error=abs(float(inp.sum())-discharged-residual)
    return a,inp,dict(meta,input_volume=float(inp.sum()),terminal_volume=discharged,
          routing_residual=residual,mass_error=error,storage_tau=storage_tau)

@njit(cache=True)
def queue_probe(q:np.ndarray,capacity:float,buffer:float):
    """Finite buffer, service-before-spill, initially dry. q is volume per unit tick.
    A standalone diagnostic: its spill is NOT subtracted from another probe.
    """
    stored=0.; discharged=0.; spilled=0.; maxstored=0.; duration=0; first=-1
    out=np.zeros(q.size); spill=np.zeros(q.size); inventory=np.zeros(q.size)
    for t in range(q.size):
        avail=stored+q[t]
        release=min(capacity,avail)
        rem=avail-release
        excess=max(0.,rem-buffer)
        stored=rem-excess
        discharged+=release; spilled+=excess
        out[t]=release; spill[t]=excess; inventory[t]=stored
        if stored>maxstored: maxstored=stored
        if excess>1.e-10:
            duration+=1
            if first<0: first=t
    return spilled,discharged,stored,maxstored,duration,first,out,spill,inventory

@njit(cache=True)
def queue_grid(q,caps,buffers):
    arr=np.zeros((len(caps)*len(buffers),8))
    idx=0
    for c in caps:
        for b in buffers:
            z=queue_probe(q,c,b)
            arr[idx,0]=c;arr[idx,1]=b;arr[idx,2]=z[0];arr[idx,3]=z[1];arr[idx,4]=z[2]
            arr[idx,5]=z[3];arr[idx,6]=z[4];arr[idx,7]=z[5]
            idx+=1
    return arr


def node_metrics(tagged:np.ndarray)->dict:
    q=tagged.sum(axis=0)
    den=tagged.max(axis=1).sum()
    peak=float(q.max())
    return dict(peak=peak,volume=float(q.sum()),synchrony=float(peak/den) if den else 0.,
                peak_time=int(np.argmax(q)),source_peak_sum=float(den),
                effective_sources=int(np.sum(tagged.sum(axis=1)>1.e-9)))

@lru_cache(maxsize=None)
def binary_trees(labels:tuple):
    if len(labels)==1: return (labels[0],)
    trees=[]
    # canonical split: smallest label always on the left; no orientation duplicates.
    rest=labels[1:]
    for mask in range(1<<len(rest)):
        left=(labels[0],)+tuple(x for i,x in enumerate(rest) if mask>>i&1)
        right=tuple(x for i,x in enumerate(rest) if not(mask>>i&1))
        if not right: continue
        for a in binary_trees(tuple(sorted(left))):
            for b in binary_trees(tuple(sorted(right))): trees.append((a,b))
    return tuple(trees)


def tree_signature(tree):
    return tree if isinstance(tree,str) else '('+','.join(sorted([tree_signature(tree[0]),tree_signature(tree[1])]))+')'


def tree_spec(base:Spec,tree,variant:str)->Spec:
    # Applicable to non-storage CDO, Kadamaian, and unresolved Kuranji uncertainty refinements.
    from copy import deepcopy
    spec=deepcopy(base)
    spec.variant=variant
    names={s:base.names[s] for s in base.sources};edges=[];counter=[0]
    root_target = 'Z' if base.case=='KURANJI' else 'R'
    def visit(t,isroot=False):
        if isinstance(t,str): return t
        a=visit(t[0]);b=visit(t[1])
        n=root_target if isroot else f'J{counter[0]}'
        if not isroot: counter[0]+=1
        names[n]=base.names.get(n,'Hypothetical merge '+n) if isroot else 'Counterfactual merge '+n
        edges.extend([e(a,n),e(b,n)])
        return n
    visit(tree,True)
    if base.case=='KURANJI':
        names['R']=base.names['R']; edges.append(e('Z','R'))
    names['O']=base.names['O'];edges.append(e('R','O'))
    spec.names=names;spec.edges=edges;spec.storage={}
    spec.limitations='HYPOTHETICAL REFINEMENT / REWIRING. Not mapped site geometry. '+base.limitations
    return spec


def change_hue(base:Spec,which:str)->Spec:
    from copy import deepcopy
    s=deepcopy(base);s.variant=which
    if which=='Bo_before_Hue_counterfactual':
        s.edges=[(u,('J0' if u=='S2' and v=='J1' else v),d,f) for u,v,d,f in s.edges]
    elif which=='residual_at_Hue_uncertainty':
        s.edges=[(u,('U' if u=='L' and v=='J1' else v),d,f) for u,v,d,f in s.edges]
    else: raise ValueError(which)
    s.limitations='HYPOTHETICAL / UNCERTAINTY LOCATION, not asserted real. '+base.limitations
    return s


def topology_metrics(spec:Spec)->dict:
    g=spec.graph()
    r=spec.observations['receiver'];u=spec.observations['urban']
    logical=nx.DiGraph()
    logical.add_weighted_edges_from((a,b,float(d)) for a,b,d,f in spec.edges)
    hops=[nx.shortest_path_length(logical,s,r,weight='weight') for s in spec.sources]
    share=lambda target:sum(nx.has_path(g,s,target) for s in spec.sources)/len(spec.sources)
    return dict(case=spec.case,variant=spec.variant,nodes=len(g),edges=len(spec.edges),
       source_groups=len(spec.sources),junctions=sum(g.in_degree(n)>1 for n in g),
       outlet_boundary_nodes=sum(g.out_degree(n)==0 for n in g),typed_storage_nodes=len(spec.storage),
       urban_source_fraction=share(u),receiver_source_fraction=share(r),
       receiver_hops=','.join(map(str,hops)),hop_mean=float(np.mean(hops)),hop_std=float(np.std(hops)),
       hop_mode_fraction=float(max(hops.count(h) for h in set(hops))/len(hops)))
