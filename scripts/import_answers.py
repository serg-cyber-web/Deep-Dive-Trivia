"""Import CSV with category,answer,aliases (aliases separated by |)."""
import csv,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from seed import norm
if len(sys.argv)!=2:raise SystemExit('Usage: python scripts/import_answers.py answers.csv')
with sqlite3.connect(Path(__file__).resolve().parents[1]/'game.db') as c, open(sys.argv[1],encoding='utf-8-sig',newline='') as f:
 for row in csv.DictReader(f):
  category=row['category'].strip();name=row['answer'].strip()
  if not category or not name:continue
  c.execute('INSERT OR IGNORE INTO categories(name) VALUES (?)',(category,))
  cat=c.execute('SELECT id FROM categories WHERE name=?',(category,)).fetchone()[0]
  c.execute('INSERT OR IGNORE INTO answers(category_id,name,normalized) VALUES (?,?,?)',(cat,name,norm(name)))
  aid=c.execute('SELECT id FROM answers WHERE category_id=? AND normalized=?',(cat,norm(name))).fetchone()[0]
  for alias in row.get('aliases','').split('|'):
   if norm(alias):c.execute('INSERT OR IGNORE INTO aliases(category_id,normalized,answer_id) VALUES (?,?,?)',(cat,norm(alias),aid))
print('CSV imported.')
