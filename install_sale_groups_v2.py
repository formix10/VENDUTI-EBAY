from pathlib import Path
import ast, shutil, subprocess, datetime, sys
p=Path('/home/ubuntu/VENDUTI-EBAY/latest_sold.py')
if not p.exists(): sys.exit('Modulo mancante')
old=p.read_text()
if 'def sale_group(' in old: sys.exit('Gruppi gia presenti')
if 'df["completezza"]=' not in old: sys.exit('Prima installare upgrade_completeness.py')
helper="""
def sale_group(title):
    import re
    t=str(title or '').lower()
    patterns=[
        (r'non funzionante|guast[ao]|difettos[ao]|per ricambi|for parts|broken|faulty|da riparare','Difettosa / ricambi'),
        (r'solo scatola|scatola vuota|empty box|box only','Solo scatola'),
        (r'pre.order|preordine|prenotazione','Preordine'),
        (r'lotto|bundle|con tetris|con cuffie|con giochi|con accessori|con gioco','Bundle / accessori'),
        (r'special edition|limited edition|edizione speciale|edizione limitata|play it loud|da collezione|sigillat[ao]|sealed|anniversary','Edizione speciale / collezione'),
    ]
    for pattern,group in patterns:
        if re.search(pattern,t): return group
    return 'Standard (da verificare)'
"""
new=old+'\n'+helper
new=new.replace('    df["completezza"]=df["title"].map(completeness)','    df["completezza"]=df["title"].map(completeness)\n    df["gruppo"]=df["title"].map(sale_group)',1)
anchor='    only_comparable=st.checkbox('
if anchor not in new: sys.exit('Filtro non trovato')
new=new.replace(anchor,'    group=st.selectbox("Tipologia / edizione",["Tutte"]+sorted(df["gruppo"].unique().tolist()),key="latest_group")\n    if group!="Tutte": df=df[df["gruppo"]==group]\n'+anchor,1)
new=new.replace('"famiglia","completezza","valutazione"','"famiglia","gruppo","completezza","valutazione"',1)
new=new.replace('"Modello","Completezza","Controllo titolo"','"Modello","Tipologia","Completezza","Controllo titolo"',1)
new=new.replace('confidence="Bassa" if len(valid)<5 else "Indicativa" if len(valid)<15 else "Da verificare"','confidence="Bassa" if len(valid)<5 else "Mista" if df["gruppo"].nunique()>1 else "Indicativa (titoli)"',1)
ast.parse(new)
backup=p.with_name('latest_sold.py.backup_group_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
shutil.copy2(p,backup)
try:
    p.write_text(new)
    subprocess.run(['/home/ubuntu/VENDUTI-EBAY/.venv/bin/python','-m','py_compile',str(p)],check=True)
    subprocess.run(['sudo','systemctl','restart','eolianretro.service'],check=True)
    subprocess.run(['systemctl','is-active','--quiet','eolianretro.service'],check=True)
    print('SUCCESSO: tipologie aggiunte. Backup:',backup.name)
except Exception as e:
    shutil.copy2(backup,p)
    print('ERRORE, ripristinato:',e)
    sys.exit(1)
