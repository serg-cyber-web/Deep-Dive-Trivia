import json,re,unicodedata
from collections import defaultdict
from pathlib import Path

def norm(s):
 s=''.join(c for c in unicodedata.normalize('NFKD',s.lower()) if not unicodedata.combining(c))
 return re.sub(r'\s+',' ',re.sub('[^a-z0-9 ]','',s)).strip()

def build():
 from countryinfo import CountryInfo
 import pycountry
 cats=defaultdict(dict)
 def add(cat,name,aliases=()):
  k=norm(name)
  if not k:return
  v=cats[cat].setdefault(k,{'name':name,'aliases':[]})
  for a in aliases:
   if norm(a)!=k and a not in v['aliases']:v['aliases'].append(a)
 for key,d in CountryInfo().all().items():
  name=d.get('name',key.title());region=d.get('region','')
  als={'united states':['USA','US'],'united kingdom':['UK','Britain'],'czech republic':['Czechia']}.get(key,[])
  add('Countries of the world',name,als)
  if region in ('Africa','Asia','Europe','Americas','Oceania'):add('Countries in '+region,name,als)
  add('Countries starting with '+name[0],name,als)
  if d.get('capital'):add('World capital cities',d['capital'])
 for s in pycountry.subdivisions:
  if s.country_code=='US' and s.type=='State':
   add('US states',s.name);add('US states starting with '+s.name[0],s.name)
 for el in pycountry.countries:
  pass
 fixed={
 'Planets':['Mercury','Venus','Earth','Mars','Jupiter','Saturn','Uranus','Neptune'],
 'Noble gases':['Helium','Neon','Argon','Krypton','Xenon','Radon','Oganesson'],
 'Great Lakes':['Superior','Michigan','Huron','Erie','Ontario'],
 'Chess pieces':['King','Queen','Rook','Bishop','Knight','Pawn'],
 'Countries that won the mens FIFA World Cup':['Brazil','Germany','Italy','Argentina','France','Uruguay','England','Spain'],
 'Olympic ring colors':['Blue','Yellow','Black','Green','Red'],
 'Oceans':['Pacific Ocean','Atlantic Ocean','Indian Ocean','Southern Ocean','Arctic Ocean'],
 'Mount Rushmore presidents':['George Washington','Thomas Jefferson','Theodore Roosevelt','Abraham Lincoln'],
 'Continents':['Africa','Asia','Europe','North America','South America','Australia','Antarctica'],
 'Primary and secondary rainbow colors':['Red','Orange','Yellow','Green','Blue','Indigo','Violet'],
 'Days of the week':['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'],
 'Months of the year':['January','February','March','April','May','June','July','August','September','October','November','December']}
 for cat,values in fixed.items():
  for value in values:add(cat,value,['Lake '+value] if cat=='Great Lakes' else ())
 # ISO-3166-2 administrative regions from pycountry: thousands of additional verified labels.
 from collections import Counter
 counts=Counter(s.country_code for s in pycountry.subdivisions)
 country_names={c.alpha_2:c.name for c in pycountry.countries}
 for subdivision in pycountry.subdivisions:
  if counts[subdivision.country_code]>=12:
   name=country_names.get(subdivision.country_code,subdivision.country_code)
   add('Administrative subdivisions of '+name,subdivision.name)
 # All 118 chemical element names from RDKit's periodic table.
 try:
  from rdkit import Chem
  table=Chem.GetPeriodicTable()
  for number in range(1,119):
   add('Chemical elements',table.GetElementName(number),[table.GetElementSymbol(number)])
 except ImportError:
  pass
 out={'categories':{k:list(v.values()) for k,v in cats.items() if len(v)>=3}}
 dest=Path(__file__).parent/'seed_data.json'
 dest.write_text(json.dumps(out,ensure_ascii=False),encoding='utf-8')
 return len(out['categories']),sum(map(len,out['categories'].values()))
if __name__=='__main__':print(build())
