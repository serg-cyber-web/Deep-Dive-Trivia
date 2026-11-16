"""Deep Dive: database-backed rarity trivia. Run: uvicorn app:app --reload"""
import json,random,sqlite3,time,uuid,difflib,os
from pathlib import Path
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from seed import norm
BASE=Path(__file__).parent
DB=Path(os.environ.get('DATABASE_PATH', str(BASE/'game.db')))
DB.parent.mkdir(parents=True, exist_ok=True)
app=FastAPI(title='Deep Dive Rarity Game')
app.mount('/static',StaticFiles(directory=BASE/'static'),name='static')
def connect():
 c=sqlite3.connect(DB,timeout=10);c.row_factory=sqlite3.Row;c.execute('PRAGMA journal_mode=WAL');return c

def initialize():
 with connect() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY,name TEXT UNIQUE);
 CREATE TABLE IF NOT EXISTS answers(id INTEGER PRIMARY KEY,category_id INTEGER,name TEXT,normalized TEXT,UNIQUE(category_id,normalized));
 CREATE TABLE IF NOT EXISTS aliases(category_id INTEGER,normalized TEXT,answer_id INTEGER,UNIQUE(category_id,normalized));
 CREATE TABLE IF NOT EXISTS games(id TEXT PRIMARY KEY,order_json TEXT,idx INTEGER DEFAULT 0,score INTEGER DEFAULT 0,phase TEXT DEFAULT 'answer',round_started REAL);
 CREATE TABLE IF NOT EXISTS submissions(id INTEGER PRIMARY KEY,game_id TEXT,category_id INTEGER,answer_id INTEGER,raw TEXT,created REAL);
 CREATE TABLE IF NOT EXISTS pending(id INTEGER PRIMARY KEY,category_id INTEGER,raw TEXT,normalized TEXT,seen_count INTEGER DEFAULT 1,UNIQUE(category_id,normalized));''')
  if c.execute('SELECT count(*) FROM categories').fetchone()[0]:return
  seed=json.loads((BASE/'seed_data.json').read_text())['categories']
  for name,answers in seed.items():
   cat=c.execute('INSERT INTO categories(name) VALUES (?)',(name,)).lastrowid
   for x in answers:
    a=c.execute('INSERT OR IGNORE INTO answers(category_id,name,normalized) VALUES (?,?,?)',(cat,x['name'],norm(x['name']))).lastrowid
    if not a:a=c.execute('SELECT id FROM answers WHERE category_id=? AND normalized=?',(cat,norm(x['name']))).fetchone()[0]
    for alias in x.get('aliases',[]):c.execute('INSERT OR IGNORE INTO aliases VALUES (?,?,?)',(cat,norm(alias),a))
initialize()
@app.get('/')
def index():return FileResponse(BASE/'static'/'index.html')
class Input(BaseModel):
 game_id:str
 answer:str=Field(max_length=100)
class GameID(BaseModel):game_id:str
def game(c,gid):
 g=c.execute('SELECT * FROM games WHERE id=?',(gid,)).fetchone()
 if not g:raise HTTPException(404,'Game not found')
 return g
def public(c,g):
 ids=json.loads(g['order_json']);idx=g['idx'];category=c.execute('SELECT name FROM categories WHERE id=?',(ids[min(idx,6)],)).fetchone()['name']
 return {'game_id':g['id'],'round':idx+1,'total_rounds':7,'score':g['score'],'phase':g['phase'],'question':'Name one: '+category,'seconds_left':max(0,25-(time.time()-g['round_started'])) if g['phase']=='answer' else 0}
@app.post('/api/start')
def start():
 with connect() as c:
  ids=[r['id'] for r in c.execute('SELECT id FROM categories WHERE id IN (SELECT category_id FROM answers GROUP BY category_id HAVING count(*)>=4)').fetchall()]
  chosen=random.sample(ids,7);gid=uuid.uuid4().hex
  c.execute('INSERT INTO games(id,order_json,round_started) VALUES(?,?,?)',(gid,json.dumps(chosen),time.time()))
  return public(c,game(c,gid))
@app.post('/api/submit')
def submit(data:Input):
 with connect() as c:
  c.execute('BEGIN IMMEDIATE')
  g=game(c,data.game_id)
  if g['phase']!='answer':raise HTTPException(409,'Round already finished')
  cat=json.loads(g['order_json'])[g['idx']];entered=norm(data.answer)
  expired=time.time()-g['round_started']>25.7
  if not entered and not expired:return {'status':'retry','message':'Type an answer.'}
  found=None
  if entered and not expired:
   found=c.execute('SELECT * FROM answers WHERE category_id=? AND normalized=?',(cat,entered)).fetchone()
   if found is None:found=c.execute('SELECT a.* FROM aliases l JOIN answers a ON a.id=l.answer_id WHERE l.category_id=? AND l.normalized=?',(cat,entered)).fetchone()
   if found is None:
    # Very conservative fuzzy correction only to avoid silently scoring a different valid answer.
    rows=c.execute('SELECT * FROM answers WHERE category_id=?',(cat,)).fetchall()
    similar=[r for r in rows if len(entered)>=5 and abs(len(entered)-len(r['normalized']))<=2 and difflib.SequenceMatcher(None,entered,r['normalized']).ratio()>=.86]
    if len(similar)==1:found=similar[0]
  if not found and not expired:
   c.execute('INSERT INTO pending(category_id,raw,normalized) VALUES (?,?,?) ON CONFLICT(category_id,normalized) DO UPDATE SET seen_count=seen_count+1',(cat,data.answer.strip(),entered))
   return {'status':'retry','message':'Not in the verified answer bank yet. It was saved for review; you can try another answer while the timer runs.'}
  points=0;sample=0;frequency=0
  if found:
   frequency=c.execute('SELECT COUNT(*) FROM submissions WHERE category_id=? AND answer_id=?',(cat,found['id'])).fetchone()[0]
   sample=c.execute('SELECT COUNT(*) FROM submissions WHERE category_id=? AND answer_id IS NOT NULL',(cat,)).fetchone()[0]
   # No invented popularity statistic: every accepted answer earns 30 as a transparent baseline
   # until >= 30 actual responses for this category. Then use empirical frequency.
   if sample>=30:
    share=(frequency+1)/(sample+len(c.execute('SELECT id FROM answers WHERE category_id=?',(cat,)).fetchall()))
    points=10 if share>=.18 else 15 if share>=.11 else 30 if share>=.06 else 60 if share>=.025 else 85 if share>=.01 else 100
   else:points=30
  c.execute('INSERT INTO submissions(game_id,category_id,answer_id,raw,created) VALUES(?,?,?,?,?)',(g['id'],cat,found['id'] if found else None,data.answer,time.time()))
  c.execute("UPDATE games SET phase='result',score=score+? WHERE id=?",(points,g['id']))
  return {'status':'scored','points':points,'answer':found['name'] if found else None,'expired':expired,'basis':'player responses' if sample>=30 else 'equal starter score (fewer than 30 historical answers)','score':g['score']+points}
@app.post('/api/next')
def next_round(data:GameID):
 with connect() as c:
  c.execute('BEGIN IMMEDIATE');g=game(c,data.game_id)
  if g['phase']!='result':raise HTTPException(409,'Submit an answer first')
  if g['idx']==6:
   c.execute("UPDATE games SET phase='finished' WHERE id=?",(g['id'],))
   return {'finished':True,'score':g['score'],'depth_m':g['score']*10}
  c.execute("UPDATE games SET idx=idx+1,phase='answer',round_started=? WHERE id=?",(time.time(),g['id']))
  return public(c,game(c,g['id']))
@app.get('/api/stats')
def stats():
 with connect() as c:return {'categories':c.execute('SELECT count(*) FROM categories').fetchone()[0],'accepted_answers':c.execute('SELECT count(*) FROM answers').fetchone()[0],'player_submissions':c.execute('SELECT count(*) FROM submissions').fetchone()[0],'pending_answers':c.execute('SELECT count(*) FROM pending').fetchone()[0]}
