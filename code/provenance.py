from pathlib import Path
import hashlib,json,csv
from model import reference_specs
root=Path(__file__).resolve().parents[1];data=root.parent
patterns={
'CDO':'Focused_CDO_Kitanglad_Deep_Terrain_Hydrology_Simulation_Analysis (1) (1) (1) (1) (1)(8).pdf',
'MANADO':'Tondano_Tikala_Manado_Deep_Terrain_Hydrology_Topology_Simulation_Analysis (1).pdf',
'KURANJI':'Batang_Kuranji_Padang_Deep_Terrain_Hydrology_Topology_Simulation_Analysis (1).pdf',
'HUE':'Huong_Hue_Deep_Terrain_Hydrology_Topology_Simulation_Analysis (1).pdf',
'KADAMAIAN':'Kadamaian_Panataran_Kota_Belud_Deep_Terrain_Hydrology_Topology_Simulation_Analysis (1).pdf',
'HATYAI':'U_Tapao_Khlong_Wat_Hat_Yai_Deep_Terrain_Hydrology_Topology_Simulation_Analysis (1).pdf'}
manifest=[];edges=[];nodes=[]
for i,s in enumerate(reference_specs()):
 p=data/patterns[s.case]
 if p.exists():manifest.append(dict(cite_id='D'+str(i+1),case=s.case,filename=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
 for n,name in s.names.items():
  nodes.append(dict(case=s.case,node_id=n,label=name,type=('source' if n in s.sources else ('routing_storage' if n in s.storage else ('probe' if n in s.observations.values() else 'connection_or_boundary'))),source=s.provenance))
 for u,v,d,f in s.edges:
  status='report-supported coarse relationship'
  if s.case in ['KURANJI','HATYAI']:status='report-supported membership; exact point junction aggregated / unspecified'
  if s.case=='HUE' and u=='L':status='uncertain residual location: provisional Sinh injection; alternative tested'
  if s.case=='KADAMAIAN' and v=='O':status='receiving boundary aggregate; not verified single physical outlet'
  if s.case=='MANADO' and (u.startswith('S') or v.startswith('S')):status='conceptual storage/control ordering from report; not surveyed'
  edges.append(dict(case=s.case,from_node=u,to_node=v,evidence_status=status,source=s.provenance,
   delay_rule='one logical link in unit-delay mode; synthetic 1-4 ticks in heterogeneous mode' if d else 'zero-delay control connector',
   baseline_split=f,split_status='assumed equal split, not measured' if f!=1 else 'all routed load to next coarse node',
   limitations=s.limitations))
(root/'inputs/source_manifest.json').write_text(json.dumps(manifest,indent=2))
for rows,name in [(edges,'edge_evidence_register.csv'),(nodes,'node_register.csv')]:
 with open(root/'inputs'/name,'w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print('Source hashes and',len(edges),'edge evidence records written.')
