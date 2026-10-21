#!/usr/bin/env python3
"""Install an additive, read-only market-trends tab on the VPS."""
from pathlib import Path
from datetime import datetime
import ast
import shutil
import subprocess
import sys

root = Path("/home/ubuntu/VENDUTI-EBAY")
dashboard = root / "dashboard.py"
module = root / "market_trends.py"
backup = root / ("dashboard.py.backup_market_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
if not dashboard.is_file():
    sys.exit("ERRORE: dashboard.py non trovato")
old_dashboard = dashboard.read_text()
old_module = module.read_text() if module.exists() else None

module_text = r'''import re
import pandas as pd
import streamlit as st

def product_type(title):
    t = str(title or "").lower()
    if re.search(r"\b(lotto|lot|bundle|stock)\b", t):
        return "Lotti"
    if re.search(r"\b(pokemon|pokémon|one piece|tcg|trading cards?|carte)\b", t):
        return "Carte collezionabili"
    if re.search(r"\b(controller|joy[ -]?con|gamepad|alimentatore|caricatore|custodia|cavo|accessori?)\b", t):
        return "Accessori"
    if re.search(r"\b(console|game\s*boy|gameboy|nintendo|switch|3ds|2ds|dsi|psp|ps vita|playstation|ps[2345]|xbox|sega|atari)\b", t):
        return "Console / giochi (indicativo)"
    return "Altro / da classificare"

def show(sales, classify):
    st.subheader("📈 Tendenze di mercato")
    st.caption("Analisi dei soli annunci raccolti, non dell'intero mercato eBay.")
    if sales.empty:
        st.info("Non ci sono ancora vendite da analizzare.")
        return
    df = sales.copy()
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["date"] = pd.to_datetime(df["sold_at"], errors="coerce", utc=True)
    df["famiglia"] = df["title"].fillna("").apply(classify)
    df["tipo"] = df["title"].fillna("").map(product_type)
    cats = sorted(df["category_name"].dropna().unique().tolist())
    selected = st.multiselect("Categorie eBay", cats, default=cats, key="trend_categories")
    df = df[df["category_name"].isin(selected)]
    types = sorted(df["tipo"].dropna().unique().tolist())
    selected_types = st.multiselect("Tipologie", types, default=types, key="trend_types")
    df = df[df["tipo"].isin(selected_types)]
    days = st.selectbox("Confronta periodi di", [30,60,90,180], index=1, format_func=lambda x: str(x)+" giorni")
    now = pd.Timestamp.now(tz="UTC")
    cut = now - pd.Timedelta(days=days)
    prior = cut - pd.Timedelta(days=days)
    current = df[(df["date"] >= cut) & (df["date"] <= now)].copy()
    previous = df[(df["date"] >= prior) & (df["date"] < cut)].copy()
    a,b,c = st.columns(3)
    a.metric("Venduti recenti", len(current))
    b.metric("Venduti periodo precedente", len(previous))
    c.metric("Prezzo mediano recente", ("€%.2f" % current["price"].median()) if current["price"].notna().any() else "—")
    st.subheader("🏆 Articoli più venduti")
    if not current.empty:
        rank = current.groupby(["tipo","famiglia"], dropna=False).agg(venduti=("id","count"), mediana=("price","median"), media=("price","mean")).reset_index().sort_values("venduti",ascending=False)
        st.dataframe(rank, use_container_width=True, hide_index=True)
    else:
        st.info("Nessuna vendita nel periodo scelto.")
    st.subheader("🚀 Segnali di crescita e calo")
    curr = current.groupby(["tipo","famiglia"]).size().rename("recenti")
    prev = previous.groupby(["tipo","famiglia"]).size().rename("precedenti")
    trend = pd.concat([curr,prev],axis=1).fillna(0).astype(int).reset_index()
    if not trend.empty:
        trend["differenza"] = trend["recenti"] - trend["precedenti"]
        trend["variazione_%"] = trend.apply(lambda r: round(100*(r["recenti"]/r["precedenti"]-1),1) if r["precedenti"] else None, axis=1)
        trend["segnale"] = trend.apply(lambda r: "Campione piccolo" if r["recenti"]+r["precedenti"] < 5 else ("Nuovo segnale" if not r["precedenti"] else ("In crescita" if r["differenza"]>0 else ("In calo" if r["differenza"]<0 else "Stabile"))), axis=1)
        st.dataframe(trend.sort_values(["differenza","recenti"],ascending=False),use_container_width=True,hide_index=True)
        st.download_button("Scarica tendenze CSV",trend.to_csv(index=False).encode("utf-8-sig"),file_name="tendenze_eolianretro.csv",mime="text/csv")
    else:
        st.info("Nessun dato nei due periodi.")
    st.subheader("📅 Vendite settimanali")
    dated = df.dropna(subset=["date"])
    dated = dated[(dated["date"] >= prior) & (dated["date"] <= now)]
    if not dated.empty:
        st.line_chart(dated.set_index("date").resample("W").size().rename("Venduti"))
    st.warning("I dati provengono dalle categorie e dalle pagine effettivamente raccolte. Il confronto non misura direttamente la domanda: disponibilità, raccolte parziali, lotti e campioni piccoli possono alterare i risultati.")
'''

try:
    if 'from market_trends import show as show_market_trends' in old_dashboard:
        print("Scheda già installata: nessuna modifica necessaria.")
        sys.exit(0)
    import re
    m = re.search(r'^(?P<indent>\s*)tab1\s*,\s*tab2\s*,\s*tab3\s*,\s*tab4\s*=\s*st\.tabs\((?P<tabs>\[[^\n]*\])\)', old_dashboard, re.M)
    if not m:
        raise RuntimeError("Non trovo la dichiarazione delle quattro schede; nessuna modifica.")
    tabs = ast.literal_eval(m.group("tabs"))
    if len(tabs) != 4:
        raise RuntimeError("Numero schede inatteso")
    tabs.append("📈 Tendenze di mercato")
    replacement = m.group("indent") + "tab1,tab2,tab3,tab4,tab5 = st.tabs(" + repr(tabs) + ")"
    new_dashboard = old_dashboard[:m.start()] + replacement + old_dashboard[m.end():]
    new_dashboard = "from market_trends import show as show_market_trends\n" + new_dashboard
    new_dashboard += "\nwith tab5:\n    show_market_trends(sales, classify)\n"
    ast.parse(module_text)
    ast.parse(new_dashboard)
    shutil.copy2(dashboard, backup)
    module.write_text(module_text)
    dashboard.write_text(new_dashboard)
    subprocess.run([str(root / ".venv/bin/python"),"-m","py_compile",str(dashboard),str(module)],check=True)
    subprocess.run(["sudo","systemctl","restart","eolianretro.service"],check=True)
    subprocess.run(["systemctl","is-active","--quiet","eolianretro.service"],check=True)
    print("SUCCESSO: scheda Tendenze di mercato installata.")
    print("Backup:",backup.name)
except Exception as exc:
    if backup.exists():
        shutil.copy2(backup,dashboard)
    if old_module is None:
        module.unlink(missing_ok=True)
    else:
        module.write_text(old_module)
    print("ERRORE:",exc)
    print("File ripristinati.")
    sys.exit(1)
