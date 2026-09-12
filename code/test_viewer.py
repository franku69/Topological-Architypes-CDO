from pathlib import Path
from playwright.sync_api import sync_playwright
import json,subprocess
import numpy as np
from model import queue_probe
root=Path(__file__).resolve().parents[1];html=root.parent/'SEA_Topology_Simulation_Explorer.html'
records=json.loads((root/'results/viewer_series.json').read_text())
cases=[]
for r in records:
 q=np.asarray(r['tagged']).sum(axis=0)
 for c,b in [(0.,10.),(2.,0.),(5.,10.),(20.,30.)]:
  full=np.r_[q,np.zeros(200)]
  z=queue_probe(full,c,b)
  cases.append(dict(q=q.tolist(),capacity=c,buffer=b,expected=[float(z[0]),float(z[1]),float(z[2])]))
p=root/'qa/viewer_test_cases.json';p.write_text(json.dumps(cases))
js="""const fs=require('fs'),{queueModel}=require(process.argv[1]);const a=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));let max=0;for(const x of a){const z=queueModel(x.q,x.capacity,x.buffer);const actual=[z.spillTotal,z.delivered,z.remaining];actual.forEach((v,i)=>max=Math.max(max,Math.abs(v-x.expected[i])))}console.log(JSON.stringify({comparisons:a.length,max_abs_error:max}));if(max>1e-7)process.exit(1);"""
r=subprocess.run(['node','-e',js,str(root/'code/viewer_core.js'),str(p)],capture_output=True,text=True,check=True)
parity=json.loads(r.stdout);print(parity)
errors=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':1200,'height':1000});page.on('pageerror',lambda err:errors.append(str(err)))
 page.set_content(html.read_text(encoding='utf-8'), wait_until='load');page.wait_for_timeout(700)
 for case in ['CDO','MANADO','KURANJI','HUE','KADAMAIAN','HATYAI']:
  page.select_option('#site',case);page.select_option('#role','receiver');page.wait_for_timeout(70)
  text=page.locator('#stats').inner_text();assert 'NaN' not in text
  assert page.locator('#graph').evaluate('(e)=>e.complete&&e.naturalWidth>0')
  if case in ['MANADO','HUE']:page.select_option('#tau','8')
 page.select_option('#site','CDO');page.select_option('#role','receiver');page.screenshot(path=str(root/'qa/viewer_desktop.png'),full_page=True)
 page.set_viewport_size({'width':390,'height':850});page.select_option('#site','HUE');page.select_option('#role','urban');page.screenshot(path=str(root/'qa/viewer_mobile.png'),full_page=True)
 page.fill('#capacity','0');page.locator('#capacity').dispatch_event('change');assert 'NaN' not in page.locator('#stats').inner_text()
 page.fill('#capacity','0.05');page.locator('#capacity').dispatch_event('change');assert page.locator('#capacity').input_value()=='0.1'
 page.locator('#play').click();page.wait_for_timeout(220);assert int(page.locator('#tick').input_value())>0;page.locator('#play').click()
 overflow=page.evaluate('document.documentElement.scrollWidth>window.innerWidth+2')
 browser.close()
assert not errors,errors
assert not overflow,'Horizontal page overflow on mobile'
log=dict(**parity,browser_errors=errors,six_cases_opened=True,desktop_and_mobile_checked=True,horizontal_mobile_overflow=overflow)
(root/'results/viewer_validation.json').write_text(json.dumps(log,indent=2));print(log)
