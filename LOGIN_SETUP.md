# Login-Setup (Option A)

## ✅ Was implementiert wurde:

1. **streamlit-authenticator** für sauberes Login (statt Browser-Popup)
2. **Session-Cookie** (30 Tage) - kein ständiges neu einloggen
3. **Logout-Button** in Sidebar
4. User-Selector entfernt - Username kommt automatisch vom Login

---

## 📦 Installation (einmalig):

```bash
cd /opt/matchhub
pip install -r requirements.txt
```

---

## 🔐 Passwörter setzen (einmalig):

### 1. Ändere die Passwörter in generate_passwords.py

```python
passwords = ["dein_martin_passwort", "dein_christoph_passwort"]
```

### 2. Generiere Hashes:

```bash
python3 generate_passwords.py
```

### 3. Kopiere die Hashes in data/auth.yaml

Ersetze die Placeholder-Hashes unter `credentials.usernames.martin.password` und `credentials.usernames.christoph.password`

---

## 🚀 Starten:

```bash
streamlit run app.py
```

**Jetzt gibt es ein Login-Formular** statt Browser-Popup:
- Username: `martin` oder `christoph`
- Password: Was du in Schritt 1 gesetzt hast
- Session bleibt 30 Tage gültig
- Logout-Button in Sidebar

---

## 📱 Mobile:

- **Kein nerviges Browser-Popup mehr**
- Passwort-Manager funktioniert normal
- Session bleibt gespeichert
- Wie eine echte App

---

## 🔧 Nginx (optional):

Du kannst Basic Auth in Nginx **komplett rausnehmen** oder nur als zusätzliche Schicht behalten.

### Basic Auth entfernen:

In deiner nginx config (`/etc/nginx/sites-available/matchhub`):

```nginx
location / {
    # Entferne diese Zeilen:
    # auth_basic "MatchHub";
    # auth_basic_user_file /etc/nginx/.htpasswd;
    
    proxy_pass http://localhost:8501;
    # ... rest bleibt
}
```

Dann: `sudo nginx -t && sudo systemctl reload nginx`
