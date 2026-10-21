#!/usr/bin/env python3
"""Add a latest-sold-by-model view without changing the SQLite database."""
from pathlib import Path
from datetime import datetime
import ast, re, shutil, subprocess, sys
root=Path("/home/ubuntu/VENDUTI-EBAY")
dash=root/"dashboard.py"
mod=root/"latest_sold.py"
backup=root/("dashboard.py.backup_latest_"+datetime.now().strftime("%Y%m%d_%H%M%S"))
if not dash.is_file(): sys.exit("ERRORE: dashboard.py non trovato")
old=dash.read_text()
old_mod=mod.read_text() if mod.exists() else None
module = r'''import pandas as pd
import streamlit as st

def show(sales, classify):
    st.subheader("🕒 Ultimi venduti per prodotto")
    st.caption("Annunci ordinati per data di vendita (sold_at), non per data di importazione. Prezzi riportati da SoldComps: verifica i singoli annunci, soprattutto le proposte accettate.")
    if sales.empty:
        st.info("Nessun annuncio raccolto.")
        return
    df=sales.copy()
    df["famiglia"]=df["title"].fillna("").apply(classify)
    df["date"]=pd.to_datetime(df["sold_at"],errors="coerce",utc=True)
    df["price"]=pd.to_numeric(df["price"],errors="coerce")
    df=df.dropna(subset=["date"])
    df=df[df["date"]<=pd.Timestamp.now(tz="UTC")]
    if df.empty:
        st.info("Non ci sono annunci con una data di vendita valida.")
        return
    cats=sorted(df["category_name"].dropna().unique().tolist())
    category=st.selectbox("Categoria eBay",["Tutte"]+cats,key="latest_cat")
    if category!="Tutte":
        df=df[df["category_name"]==category]
    fams=sorted(df["famiglia"].dropna().unique().tolist())
    family=st.selectbox("Modello / famiglia",["Tutte"]+fams,key="latest_family")
    if family!="Tutte":
        df=df[df["famiglia"]==family]
    query=st.text_input("Parole nel titolo (facoltativo)",placeholder="Es. DS Lite, console, funzionante",key="latest_query")
    if query.strip():
        for word in query.split():
            df=df[df["title"].fillna("").str.contains(word,case=False,regex=False)]
    c1,c2=st.columns(2)
    days=c1.selectbox("Venduti negli ultimi", [7,14,30,60,90,180,365,0],index=2,format_func=lambda n: "Tutte le date disponibili" if n==0 else str(n)+" giorni",key="latest_days")
    n=c2.selectbox("Numero di annunci recenti",[10,20,30,50,100],index=1,key="latest_n")
    if days:
        df=df[df["date"]>=pd.Timestamp.now(tz="UTC")-pd.Timedelta(days=days)]
    df=df.sort_values(["date","id"],ascending=[False,False])
    df=df.head(n).copy()
    if df.empty:
        st.warning("Nessun venduto corrisponde ai filtri. Prova ad ampliare il periodo.")
        return
    prices=df.loc[(df["price"]>=0)&(df["currency"]=="EUR"),"price"].dropna()
    a,b,c=st.columns(3)
    a.metric("Ultimi annunci trovati",len(df))
    b.metric("Mediana annunci selezionati",("€%.2f"%prices.median()) if len(prices) else "—")
    c.metric("Prezzo minimo annunci",("€%.2f"%prices.min()) if len(prices) else "—")
    st.caption("La mediana è calcolata SOLO sui risultati visualizzati in EUR. Non equivale a una quotazione certificata di console complete.")
    display=df[["sold_at","title","famiglia","price","currency","category_name","url"]].copy()
    display=display.rename(columns={"sold_at":"Data vendita","title":"Titolo","famiglia":"Modello","price":"Prezzo","currency":"Valuta","category_name":"Categoria","url":"Annuncio eBay"})
    st.dataframe(display,use_container_width=True,hide_index=True,column_config={"Annuncio eBay":st.column_config.LinkColumn("Apri annuncio")})
    st.download_button("Esporta ultimi venduti CSV",df.to_csv(index=False).encode("utf-8-sig"),file_name="ultimi_venduti_eolianretro.csv",mime="text/csv")
    st.warning("Possibili lotti, accessori, giochi e articoli difettosi: controlla i titoli prima di confrontare i prezzi. La raccolta SoldComps potrebbe non includere tutti i venduti e il prezzo di un'offerta accettata potrebbe non essere verificabile.")
'''
try:
    if "from latest_sold import show as show_latest_sold" in old:
        print("SUCCESSO: scheda Ultimi venduti già installata.")
        sys.exit(0)
    m=re.search(r'^(?P<indent>[ \t]*)(?P<vars>tab1\s*,\s*tab2\s*,\s*tab3\s*,\s*tab4(?:\s*,\s*tab5)?)\s*=\s*st\.tabs\((?P<tabs>\[[^\n]*\])\)',old,re.M)
    if not m: raise RuntimeError("Non riconosco le schede della dashboard: nessuna modifica.")
    tabs=ast.literal_eval(m.group("tabs"))
    vars=[x.strip() for x in m.group("vars").split(",")]
    if len(tabs)!=len(vars): raise RuntimeError("Numero schede non coerente")
    if any("Ultimi venduti per prodotto" in x for x in tabs): raise RuntimeError("Scheda già presente ma import mancante; fermato per sicurezza")
    next_tab="tab"+str(len(vars)+1)
    tabs.append("🕒 Ultimi venduti per prodotto")
    new=old[:m.start()]+m.group("indent")+(",".join(vars+[next_tab]))+" = st.tabs("+repr(tabs)+")"+old[m.end():]
    new="from latest_sold import show as show_latest_sold\n"+new
    new+="\nwith "+next_tab+":\n    show_latest_sold(sales, classify)\n"
    ast.parse(new)
    ast.parse(module)
    shutil.copy2(dash,backup)
    mod.write_text(module)
    dash.write_text(new)
    subprocess.run([str(root/".venv/bin/python"),"-m","py_compile",str(dash),str(mod)],check=True)
    subprocess.run(["sudo","systemctl","restart","eolianretro.service"],check=True)
    subprocess.run(["systemctl","is-active","--quiet","eolianretro.service"],check=True)
    print("SUCCESSO: scheda Ultimi venduti per prodotto installata.")
    print("Backup:",backup.name)
except Exception as exc:
    if backup.exists(): shutil.copy2(backup,dash)
    if old_mod is None: mod.unlink(missing_ok=True)
    else: mod.write_text(old_mod)
    print("ERRORE:",exc)
    print("File precedenti ripristinati.")
    sys.exit(1)
