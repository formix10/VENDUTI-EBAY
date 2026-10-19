import os
import re
import requests
from storage import connect, monthly_calls, utcnow

API_URL = "https://api.sold-comps.com/v1/scrape/category"
TIMEOUT = 45

def normalize_items(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("items", "results", "listings", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            for sub in ("items", "results", "listings"):
                if isinstance(value.get(sub), list):
                    return value[sub]
    return []

def number(value):
    if isinstance(value, dict):
        value = value.get("value", value.get("amount"))
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        v = re.sub(r"[^0-9.,]", "", value)
        if "," in v and "." in v:
            v = v.replace(",", "") if v.rfind(".") > v.rfind(",") else v.replace(".", "").replace(",", ".")
        elif "," in v:
            v = v.replace(",", ".")
        try:
            return float(v)
        except ValueError:
            pass
    return None

def collect(category_id):
    key = os.getenv("SOLDCOMPS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Chiave SOLDCOMPS_API_KEY mancante sulla VPS.")
    with connect() as con:
        category = con.execute("SELECT * FROM categories WHERE id=? AND enabled=1", (category_id,)).fetchone()
        if not category:
            raise RuntimeError("Categoria inesistente o disattivata.")
        cap = min(max(int(os.getenv("MONTHLY_REQUEST_CAP", "90")), 1), 90)
        if monthly_calls(con) >= cap:
            raise RuntimeError(f"Limite prudenziale raggiunto: {cap} richieste questo mese (UTC).")
        # Record BEFORE sending request: errors and timeouts may still consume API quota.
        cur = con.execute("INSERT INTO api_calls(created_at, category_id, status) VALUES (?,?,?)",
                          (utcnow(), category_id, "started"))
        call_id = cur.lastrowid
        con.commit()
        minimum = float(category["min_price"])

    try:
        response = requests.get(API_URL,
            params={"categoryId": category_id, "ebaySite": os.getenv("SOLD_COMPS_SITE", "EBAY_IT"),
                    "page": 1, "count": 240, "sortOrder": "endedRecently", "minPrice": minimum},
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            timeout=TIMEOUT)
        with connect() as con:
            con.execute("UPDATE api_calls SET status=?, http_code=? WHERE id=?",
                        ("http_response", response.status_code, call_id))
            con.commit()
        if not response.ok:
            # Never expose response headers or authentication secrets.
            raise RuntimeError(f"SoldComps ha risposto HTTP {response.status_code}. Verifica accesso API, piano e parametri.")
        payload = response.json()
        items = normalize_items(payload)
        if isinstance(payload, dict) and not items and any(k in payload for k in ("error", "message")):
            raise RuntimeError("SoldComps non ha restituito risultati validi: controlla il messaggio nella dashboard del servizio.")
        added = 0
        with connect() as con:
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or item.get("name") or "").strip()
                price = number(item.get("price", item.get("soldPrice")))
                if not title or price is None or price < minimum:
                    continue
                ext_id = str(item.get("itemId") or item.get("item_id") or item.get("id") or "").strip() or None
                url = str(item.get("url") or item.get("itemUrl") or "")
                sold_at = str(item.get("soldDate") or item.get("endTime") or item.get("sold_at") or "")
                # Without an item ID, avoid duplicate imports by using stable listing attributes.
                if not ext_id:
                    import hashlib
                    ext_id = hashlib.sha256((title+"|"+str(price)+"|"+sold_at+"|"+url).encode()).hexdigest()
                image = item.get("imageUrl") or item.get("image") or ""
                if isinstance(image, dict):
                    image = image.get("url", "")
                result = con.execute("""INSERT OR IGNORE INTO sales
                  (category_id, external_id, title, price, currency, sold_at, url, image_url, captured_at)
                  VALUES (?,?,?,?,?,?,?,?,?)""",
                  (category_id, ext_id, title, price, str(item.get("currency") or "EUR"),
                   sold_at, url, str(image), utcnow()))
                added += result.rowcount
            con.execute("UPDATE api_calls SET status='success' WHERE id=?", (call_id,))
            con.commit()
        return len(items), added
    except Exception:
        with connect() as con:
            con.execute("UPDATE api_calls SET status='failed' WHERE id=? AND status!='success'", (call_id,))
            con.commit()
        raise
