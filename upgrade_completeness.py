#!/usr/bin/env python3
"""Add explicit title-based console completeness filters to latest_sold.py."""
from pathlib import Path
from datetime import datetime
import ast, shutil, subprocess, sys
root=Path("/home/ubuntu/VENDUTI-EBAY")
p=root/"latest_sold.py"
if not p.exists(): sys.exit("ERRORE: latest_sold.py non presente.")
old=p.read_text()
backup=p.with_name("latest_sold.py.backup_condition_"+datetime.now().strftime("%Y%m%d_%H%M%S"))
addition=r'''
def completeness(title):
    t=str(title or "").lower()
    import re
    boxed=bool(re.search(r"\b(con scatola|scatola originale|scatolata|scatolato|boxed|in box|cib|complete in box|con box|with box|con confezione originale)\b",t))
    complete=bool(re.search(r"\b(completa|completo|complete|full set|completissima|completissimo|cib)\b",t))
    no_box=bool(re.search(r"\b(senza scatola|no box|unboxed|loose|senza box)\b",t))
    bare=bool(re.search(r"\b(solo console|sola console|console only|senza accessori)\b",t))
    empty=bool(re.search(r"\b(solo scatola|scatola vuota|empty box|box only|solo box|only box)\b",t))
    if empty: return "Solo scatola / accessori"
    if bare: return "Solo console"
    if complete and boxed and not no_box: return "Completa con scatola"
    if complete and no_box: return "Completa senza scatola"
    if complete: return "Completa, scatola non dichiarata"
    if boxed and not no_box: return "Con scatola, completezza incerta"
    return "Non specificato"
'''
try:
    if "def completeness(title):" in old:
        print("SUCCESSO: classificazione completezza già installata.")
        sys.exit(0)
    marker='    df["valutazione"]=df["title"].map(assess)'
    if marker not in old: raise RuntimeError("Versione del modulo non riconosciuta: esegui prima upgrade_latest_sold.py")
    new=old.replace(marker,marker+'\n    df["completezza"]=df["title"].map(completeness)',1)
    needle='    only_comparable=st.checkbox('
    if needle not in new: raise RuntimeError("Filtro esistente non trovato")
    insertion='''    options=["Tutte"]+sorted(df["completezza"].dropna().unique().tolist())
    chosen=st.selectbox("Completezza / confezione dichiarata nel titolo",options,key="latest_completeness")
    if chosen!="Tutte": df=df[df["completezza"]==chosen]
'''
    new=new.replace(needle,insertion+needle,1)
    new=new.replace('df[["sold_at","title","famiglia","valutazione","price","currency","category_name","url"]]', 'df[["sold_at","title","famiglia","completezza","valutazione","price","currency","category_name","url"]]',1)
    new=new.replace('"Titolo","Modello","Controllo titolo","Prezzo"', '"Titolo","Modello","Completezza","Controllo titolo","Prezzo"',1)
    new=new+'\n'+addition
    ast.parse(new)
    shutil.copy2(p,backup)
    p.write_text(new)
    subprocess.run([str(root/".venv/bin/python"),"-m","py_compile",str(p)],check=True)
    subprocess.run(["sudo","systemctl","restart","eolianretro.service"],check=True)
    subprocess.run(["systemctl","is-active","--quiet","eolianretro.service"],check=True)
    print("SUCCESSO: completezza e scatola aggiunte ai filtri.")
    print("Backup:",backup.name)
except Exception as e:
    if backup.exists(): shutil.copy2(backup,p)
    print("ERRORE:",e)
    sys.exit(1)
