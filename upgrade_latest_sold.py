#!/usr/bin/env python3
"""Safe additive replacement of latest_sold.py; no database or API changes."""
from pathlib import Path
from datetime import datetime
import ast, shutil, subprocess, sys
root=Path("/home/ubuntu/VENDUTI-EBAY")
mod=root/"latest_sold.py"
dash=root/"dashboard.py"
if not mod.exists() or not dash.exists(): sys.exit("ERRORE: modulo o dashboard assente; nessuna modifica.")
old=mod.read_text()
backup=mod.with_name("latest_sold.py.backup_"+datetime.now().strftime("%Y%m%d_%H%M%S"))
new=r'''import re
import pandas as pd
import streamlit as st

EXCLUDE = [
    (r"\b(pre[ -]?order|preordine|prenotazione|reservation)\b", "Preordine"),
    (r"\b(lotto|lot|bundle|stock|scatol[ae]|box only|solo scatola|empty box)\b", "Lotto o confezione"),
    (r"\b(non funzionante|non funziona|guasta|guasto|difettos[ao]|per ricambi|for parts|broken|faulty|da riparare|no power|as is)\b", "Difettoso"),
    (r"\b(controller|joy[ -]?con|gamepad|cover|skin|custodia|case|dock|alimentatore|caricatore|charging|cavo|cable|ricambio|replacement|manuale|manual only|scheda madre|motherboard|display|schermo|lcd|lettore|lettori)\b", "Accessorio/ricambio"),
    (r"\b(gioco|videogioco|game only|game card|cartuccia|cartridge|cd|dvd|bluray|blu-ray|digital code|codice download)\b", "Gioco o codice"),
]
def assess(title):
    t=str(title or "").lower()
    for pattern,reason in EXCLUDE:
        if re.search(pattern,t,re.I): return reason
    return "Da verificare"

def show(sales, classify):
    st.subheader("🕒 Ultimi venduti per prodotto")
    st.caption("Ordine per data effettiva di vendita. I prezzi provengono da SoldComps, non sono verifiche indipendenti dei pagamenti.")
    if sales.empty:
        st.info("Nessun venduto salvato.")
        return
    df=sales.copy()
    df["famiglia"]=df["title"].fillna("").apply(classify)
    df["date"]=pd.to_datetime(df["sold_at"],errors="coerce",utc=True)
    df["price"]=pd.to_numeric(df["price"],errors="coerce")
    df["valutazione"]=df["title"].map(assess)
    df=df.dropna(subset=["date"])
    df=df[df["date"]<=pd.Timestamp.now(tz="UTC")]
    if df.empty:
        st.info("Nessuna data di vendita valida.")
        return
    cats=sorted(df["category_name"].dropna().unique().tolist())
    cat=st.selectbox("Categoria eBay",["Tutte"]+cats,key="latest_cat")
    if cat!="Tutte": df=df[df["category_name"]==cat]
    families=sorted(df["famiglia"].dropna().unique().tolist())
    family=st.selectbox("Modello / famiglia (selezionalo per calcolare il prezzo)",["Seleziona un modello"]+families,key="latest_family")
    query=st.text_input("Parole nel titolo (facoltativo)",placeholder="Es. console funzionante",key="latest_query")
    if family!="Seleziona un modello": df=df[df["famiglia"]==family]
    if query.strip():
        for word in query.split():
            df=df[df["title"].fillna("").str.contains(word,case=False,regex=False)]
    c1,c2=st.columns(2)
    days=c1.selectbox("Venduti negli ultimi",[7,14,30,60,90,180,365,0],index=2,format_func=lambda x: "Tutte le date" if x==0 else f"{x} giorni",key="latest_days")
    n=c2.selectbox("Numero annunci",[10,20,30,50,100],index=1,key="latest_n")
    if days: df=df[df["date"]>=pd.Timestamp.now(tz="UTC")-pd.Timedelta(days=days)]
    df=df.sort_values(["date","id"],ascending=[False,False])
    only_comparable=st.checkbox("Escludi preordini, lotti, accessori, giochi e difettosi",value=True,key="latest_comparable")
    if only_comparable: df=df[df["valutazione"]=="Da verificare"]
    df=df.head(n).copy()
    if df.empty:
        st.info("Nessun risultato. Amplia il periodo oppure disattiva l'esclusione.")
        return
    valid=df[(df["currency"].astype(str).str.upper()=="EUR") & df["price"].ge(0)]
    a,b,c=st.columns(3)
    a.metric("Annunci recenti",len(df))
    if family=="Seleziona un modello":
        b.metric("Mediana del modello","—")
        c.metric("Affidabilità","Seleziona modello")
        st.info("Seleziona un modello per ottenere una mediana: mescolare console diverse produce prezzi fuorvianti.")
    else:
        b.metric("Mediana dei selezionati",f"€{valid['price'].median():.2f}" if not valid.empty else "—")
        confidence="Bassa" if len(valid)<5 else "Indicativa" if len(valid)<15 else "Da verificare"
        c.metric("Affidabilità",confidence)
        st.caption(f"Mediana su {len(valid)} annunci in EUR, dopo i filtri. Anche i titoli non esclusi possono riferirsi a giochi o accessori: non è una quotazione certificata.")
    display=df[["sold_at","title","famiglia","valutazione","price","currency","category_name","url"]].copy()
    display.columns=["Data vendita","Titolo","Modello","Controllo titolo","Prezzo","Valuta","Categoria eBay","Apri annuncio"]
    st.dataframe(display,use_container_width=True,hide_index=True,column_config={"Apri annuncio":st.column_config.LinkColumn("Apri annuncio")})
    st.download_button("Esporta CSV",df.to_csv(index=False).encode("utf-8-sig"),file_name="ultimi_venduti_filtrati.csv",mime="text/csv")
    st.warning("Il filtro sui titoli è prudenziale ma imperfetto. Verifica gli annunci: non conosciamo sempre contenuto effettivo, condizioni, spedizione o prezzo di proposta accettata. Non tutte le vendite eBay sono necessariamente presenti.")
'''
try:
    ast.parse(new)
    if "show_latest_sold" not in dash.read_text(): raise RuntimeError("La dashboard non richiama il modulo previsto.")
    shutil.copy2(mod,backup)
    mod.write_text(new)
    subprocess.run([str(root/".venv/bin/python"),"-m","py_compile",str(mod)],check=True)
    subprocess.run(["sudo","systemctl","restart","eolianretro.service"],check=True)
    subprocess.run(["systemctl","is-active","--quiet","eolianretro.service"],check=True)
    print("SUCCESSO: prezzi per modello e filtri di confronto aggiornati.")
    print("Backup:",backup.name)
except Exception as e:
    if backup.exists(): shutil.copy2(backup,mod)
    print("ERRORE:",e)
    print("Modulo precedente ripristinato.")
    sys.exit(1)
