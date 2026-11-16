"""List unrecognized answer candidates for later human validation."""
import sqlite3
from pathlib import Path
c=sqlite3.connect(Path(__file__).resolve().parents[1]/'game.db')
for row in c.execute('SELECT c.name,p.raw,p.seen_count FROM pending p JOIN categories c ON c.id=p.category_id ORDER BY p.seen_count DESC LIMIT 100'):
 print(f'{row[0]}: {row[1]} (submitted {row[2]} times)')
