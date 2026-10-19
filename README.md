# Eolian Retrò — Venduti eBay

Dashboard autonoma per analizzare venduti eBay usando SoldComps. Il progetto parte con **zero categorie e zero venduti**; non importa database, categorie, impostazioni o credenziali del progetto sorgente.

## Funzioni
- Inserimento manuale ID categoria eBay e prezzo minimo per ciascuna categoria.
- Raccolta manuale di **una pagina per volta**, senza ricerca per parole chiave.
- Statistiche su prezzo medio, mediano e famiglie di console, ricerca testuale e filtri per prezzo.
- Database SQLite locale ed esportazione CSV.
- Contatore locale di richieste API con limite massimo prudenziale di 90 tentativi/mese UTC, inclusi errori e timeout.
- Nessun acquisto di crediti, nessuna raccolta automatica.

**Compatibilità API da verificare:** l'endpoint `/v1/scrape/category`, i suoi parametri e il diritto di usarlo sul piano gratuito devono essere confermati con una prova reale. L'app non garantisce che SoldComps permetta lo scraping di categorie complete con il piano gratuito. I risultati dipendono anche dal formato JSON restituito dal servizio.

## Installazione su VPS Linux

```bash
sudo apt update
sudo apt install -y python3 python3-venv git
git clone https://github.com/formix10/VENDUTI-EBAY.git
cd VENDUTI-EBAY
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env
```

Nel file `.env` inserisci **solo sulla VPS** la chiave privata `SOLDCOMPS_API_KEY`. Non inviare la chiave in chat e non pubblicare `.env` su GitHub.

Avvio locale per la prima verifica:

```bash
.venv/bin/streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501
```

Per accesso da remoto usare un tunnel SSH o un reverse proxy HTTPS protetto da autenticazione; **non esporre Streamlit direttamente su Internet senza protezioni**.

## Secret GitHub

Il secret GitHub Actions `SOLDCOMPS_API_KEY` è separato dall'ambiente della VPS. Non viene copiato automaticamente sulla VPS. Non aggiungere workflow che stampino il suo valore.

## Note sui limiti

Il contatore è **locale** e non equivale alla quota ufficiale SoldComps. Se la stessa chiave è usata altrove, la quota residua potrebbe essere inferiore. Il programma non esegue richieste se raggiunge il limite locale; in caso di risposta HTTP non riuscita, registra il tentativo e mostra l'errore.

Le categorie cancellate non cancellano i venduti storici già raccolti. Il raggruppamento per titolo è euristico e potrà essere migliorato.

## Preparazione per OVHcloud

Il file `deploy/venduti-ebay.service` contiene un servizio systemd di esempio che avvia la dashboard solo sull'interfaccia locale `127.0.0.1:8501`, con un utente di sistema dedicato. Prima di attivarlo occorre predisporre un ambiente Python, configurare la chiave privata nel file `.env` della VPS e verificare che l'utente di servizio abbia accesso alla cartella dei dati.

Per la prima apertura dal proprio computer utilizzare un tunnel SSH verso la porta 8501, senza esporre direttamente Streamlit su Internet. Per l'accesso pubblico occorre predisporre HTTPS e autenticazione.

I test automatici offline sono in `test_classifier.py` e `test_core.py` e possono essere eseguiti con `python -m unittest discover -p 'test_*.py' -v`. Non consumano richieste SoldComps.

Prima della raccolta reale resta da verificare la compatibilità dell'endpoint SoldComps e i permessi del piano gratuito.
