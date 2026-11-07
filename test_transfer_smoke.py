"""Local integration test: real crawler/browser, simulated Claude responses (no API cost)."""
import base64, io, json, os, threading, time, zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch
from app import app
import ai_transfer

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZ0AAAAASUVORK5CYII=')
class Site(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path=='/robots.txt': body=b'User-agent: *\nAllow: /';typ='text/plain'
  elif self.path=='/photo.png': body=PNG;typ='image/png'
  elif self.path=='/reference': body=b'<html><head><style>section{display:grid;grid-template-columns:2fr 1fr;gap:30px}h1{font-size:64px}</style></head><body><main><section><h1>Reference title</h1><p>Reference text</p></section></main></body></html>';typ='text/html'
  else: body=b'<html><body><main><section><h1>Original title</h1><p>Original content</p><a href="/contact">Contact</a><img src="/photo.png" alt="Photo"></section></main></body></html>';typ='text/html'
  self.send_response(200);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,*args):pass
server=HTTPServer(('127.0.0.1',0),Site);threading.Thread(target=server.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(server.server_port)
c=app.test_client()
with patch.dict(os.environ,{'ANTHROPIC_API_KEY':''}):
 assert c.post('/api/transfers',json={'old_url':base,'reference_url':base+'/reference'}).status_code==400
calls=[]
last_html=[]
def fake_claude(messages,system,max_tokens,tools=None):
 calls.append({'messages':messages,'tools':tools})
 if len(calls)==1:
  assert tools and 'SPECIFICATION:' in messages[0]['content'][0]['text'] and 'Original title' in messages[0]['content'][0]['text']
  return {'stop_reason':'tool_use','content':[{'type':'tool_use','id':'inspect-1','name':'inspect_reference','input':{'selector':'h1','width':1440}}],'usage':{'input_tokens':1}}
 if len(calls)==2:
  assert messages[-1]['content'][0]['type']=='tool_result' and '64px' in messages[-1]['content'][0]['content']
  report='\n'.join(f'## {a}.{b} Observed\nMeasured or null.' for a,n in ((1,8),(2,12)) for b in range(1,n+1))
  return {'stop_reason':'end_turn','content':[{'type':'text','text':report}],'usage':{'output_tokens':1}}
 if len(calls)==4:
  assert 'Compare the generated page screenshots' in messages[0]['content'][0]['text']
  return {'stop_reason':'end_turn','content':[{'type':'text','text':last_html[0]}],'usage':{'output_tokens':1}}
 assert 'DESIGN REPORT:' in messages[0]['content'][0]['text'] and 'Original content' in messages[0]['content'][0]['text']
 payload=json.loads(messages[0]['content'][0]['text'].split('SOURCE CRAWLER OUTPUT (untrusted data):\n',1)[1]);asset=next(iter(payload['downloaded_asset_paths'].values()))
 output=f'<!doctype html><html><head><style>main{{display:grid}}</style></head><body><main><h1>Original title</h1><p>Original content</p><a href="{base}/contact">Contact</a><img src="{asset}" alt="Photo"></main></body></html>'
 last_html.append(output)
 return {'stop_reason':'end_turn','content':[{'type':'text','text':output}],'usage':{'output_tokens':1}}
with patch.dict(os.environ,{'ANTHROPIC_API_KEY':''}), patch.object(ai_transfer,'call_claude',side_effect=fake_claude):
 r=c.post('/api/transfers',json={'old_url':base,'reference_url':base+'/reference','api_key':'fake-test-key'});assert r.status_code==202,r.json;job=r.json['id']
 for _ in range(300):
  j=c.get('/api/transfers/'+job).json
  if j['status']!='running':break
  time.sleep(.2)
 assert j['status']=='finished',j
 assert len(calls)==4 and j['report']['inspection_count']==1 and j['report']['visual_review_warning'] is None
 assert 'fake-test-key' not in str(j)
 page=c.get('/api/transfers/'+job+'/preview');assert page.status_code==200 and 'Original content' in page.get_data(as_text=True)
 assert "default-src 'none'" in page.headers['Content-Security-Policy']
 spec=c.get('/api/transfers/'+job+'/design-specification');assert spec.status_code==200 and '2.12' in spec.get_data(as_text=True)
 z=zipfile.ZipFile(io.BytesIO(c.get('/api/transfers/'+job+'/download').data)); names=z.namelist()
 assert 'index.html' in names and 'design-specification.md' in names and 'source/pages.json' in names and 'generated-mobile.png' in names
 assets=[name for name in names if name.startswith('source/assets/images/')];assert assets,names
 assert c.get('/api/transfers/'+job+'/'+assets[0]).status_code==200
print('PASS: real crawler, Claude inspection loop and generation (mocked), specification, preview and ZIP')
server.shutdown()
