import os
import re
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from storage import connect, monthly_calls
from collector import collect
st.set_page_config(page_title="Eolian Retrò · Venduti eBay", layout="wide", page_icon="🎮")
st.title("🎮 Eolian Retrò — Venduti eBay")
st.caption("Database indipendente · categorie e prezzi minimi personalizzati · SoldComps piano gratuito")

with connect() as con:
    cats = pd.read_sql_query("SELECT id, name, min_price, enabled FROM categories ORDER BY name", con)
    sales = pd.read_sql_query("""SELECT s.*, c.name AS category_name
        FROM sales s LEFT JOIN categories c ON c.id=s.category_id
        ORDER BY s.id DESC""", con)
    used = monthly_calls(con)

cap = min(max(int(os.getenv("MONTHLY_REQUEST_CAP", "90")), 1), 90)
a,b,c = st.columns(3)
a.metric("Categorie", len(cats))
b.metric("Venduti salvati", len(sales))
c.metric("Richieste API questo mese", f"{used}/{cap}")
st.progress(min(used/cap, 1.0))
st.caption("Il contatore locale include tentativi ed errori e non sostituisce il saldo ufficiale SoldComps.")

tab1,tab2,tab3 = st.tabs(["Categorie e raccolta", "Venduti e statistiche", "Impostazioni"])

with tab1:
    st.subheader("Aggiungi una categoria eBay")
    with st.form("new_category"):
        cat_id = st.text_input("ID numerico categoria eBay", placeholder="Es. 139971")
        cat_name = st.text_input("Nome per la dashboard", placeholder="Es. Console portatili")
        min_price = st.number_input("Prezzo minimo (€)", min_value=0.0, value=70.0, step=5.0)
        if st.form_submit_button("Salva categoria"):
            if not re.fullmatch(r"\d+", cat_id.strip()) or not cat_name.strip():
                st.error("Inserisci ID numerico e nome.")
            else:
                with connect() as con:
                    con.execute("""INSERT INTO categories(id,name,min_price,enabled) VALUES(?,?,?,1)
                        ON CONFLICT(id) DO UPDATE SET name=excluded.name,min_price=excluded.min_price,enabled=1""",
                        (cat_id.strip(), cat_name.strip(), min_price))
                    con.commit()
                st.success("Categoria salvata.")
                st.rerun()
    if cats.empty:
        st.info("Nessuna categoria inserita. Non viene importato alcun dato dal progetto originale.")
    else:
        for row in cats.itertuples():
            with st.expander(f"{row.name} · ID {row.id} · minimo €{row.min_price:.2f}"):
                col1,col2 = st.columns(2)
                with col1:
                    with st.form(f"edit_{row.id}"):
                        new_name = st.text_input("Nome", value=row.name)
                        new_min = st.number_input("Prezzo minimo", value=float(row.min_price), min_value=0.0, step=5.0)
                        enabled = st.checkbox("Categoria attiva", value=bool(row.enabled))
                        if st.form_submit_button("Aggiorna"):
                            with connect() as con:
                                con.execute("UPDATE categories SET name=?,min_price=?,enabled=? WHERE id=?",
                                            (new_name.strip(),new_min,int(enabled),str(row.id)))
                                con.commit()
                            st.rerun()
                with col2:
                    st.write("Una richiesta raccoglie solo la prima pagina di venduti recenti (fino a 240, se supportato dal piano).")
                    if st.button("Raccogli venduti ora", key=f"collect_{row.id}", disabled=not bool(row.enabled) or used>=cap):
                        with st.spinner("Richiesta a SoldComps in corso…"):
                            try:
                                total, added = collect(str(row.id))
                                st.success(f"Risultati ricevuti: {total}. Nuovi venduti salvati: {added}.")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))
                    if st.button("Elimina categoria", key=f"delete_{row.id}"):
                        with connect() as con:
                            con.execute("DELETE FROM categories WHERE id=?", (str(row.id),))
                            con.commit()
                        st.rerun()

with tab2:
    if sales.empty:
        st.info("Ancora nessun venduto raccolto.")
    else:
        categories = sorted(sales["category_name"].dropna().unique().tolist())
        selected = st.multiselect("Filtra categorie", categories, default=categories)
        filtered = sales[sales["category_name"].isin(selected)].copy()
        if not filtered.empty:
            filtered["price"] = pd.to_numeric(filtered["price"], errors="coerce")
            x,y,z = st.columns(3)
            x.metric("Venduti", len(filtered))
            y.metric("Prezzo medio", f"€{filtered['price'].mean():.2f}")
            z.metric("Prezzo mediano", f"€{filtered['price'].median():.2f}")
            st.subheader("Prezzi per categoria")
            st.bar_chart(filtered.groupby("category_name")["price"].median())
            st.subheader("Famiglie di titoli (prime 3 parole)")
            filtered["famiglia"] = filtered["title"].fillna("").apply(
                lambda s: " ".join(re.findall(r"[\wÀ-ÿ]+", s.lower())[:3]) or "Altro")
            families = filtered.groupby("famiglia").agg(venduti=("id","count"), prezzo_medio=("price","mean"))
            st.dataframe(families.sort_values("venduti", ascending=False).head(50), use_container_width=True)
            st.subheader("Elenco venduti")
            st.dataframe(filtered[["title","price","currency","sold_at","category_name","url"]],
                         use_container_width=True, hide_index=True)
            st.download_button("Esporta CSV", filtered.to_csv(index=False).encode("utf-8-sig"),
                               file_name="venduti_ebay.csv", mime="text/csv")

with tab3:
    st.write("Chiave API configurata:", "Sì" if os.getenv("SOLDCOMPS_API_KEY") else "No")
    st.write("Database:", str(os.getenv("DB_PATH", "data/venduti.sqlite3")))
    st.write("Limite locale richieste mensili:", cap)
    st.warning("Il piano gratuito potrebbe non autorizzare l'endpoint di raccolta per categoria. In tal caso l'app segnalerà il codice HTTP, senza tentare acquisti.")
    st.info("Il Secret di GitHub Actions non è automaticamente disponibile sulla VPS. Inserire la chiave soltanto nel file .env della VPS, mai nel repository.")
