import uuid
import requests
from flask import Flask, redirect, render_template, session, request, url_for
import msal
import app_config

app = Flask(__name__)
app.config.from_object(app_config)

# Session konfiguráció
app.secret_key = app_config.Config.SECRET_KEY

@app.route("/")
def index():
    if not session.get("user"):
        return redirect(url_for("login"))
    
    return render_template('index.html', user=session["user"])

@app.route("/login")
def login():
    session["state"] = str(uuid.uuid4())
    auth_url = _build_auth_url(scopes=app_config.Config.SCOPE, state=session["state"])
    return redirect(auth_url)

@app.route("/getAToken")
def authorized():
    if request.args.get('state') != session.get("state"):
        return redirect(url_for("index"))
    
    if "error" in request.args:
        return render_template("auth_error.html", result=request.args)
    
    # Egyszerű token lekérés - ne tároljuk a cache-t sessionben
    result = _build_msal_app().acquire_token_by_authorization_code(
        request.args['code'],
        scopes=app_config.Config.SCOPE,
        redirect_uri=app_config.Config.REDIRECT_URI
    )
    
    if "error" in result:
        return render_template("auth_error.html", result=result)
    
    # Csak a szükséges user adatokat tároljuk
    id_token_claims = result.get("id_token_claims", {})
    session["user"] = {
        "name": id_token_claims.get("name"),
        "preferred_username": id_token_claims.get("preferred_username"),
        "email": id_token_claims.get("preferred_username")  # email cím
    }
    
    # További felhasználói adatok lekérése Graph API-ból
    access_token = result.get("access_token")
    if access_token:
        try:
            user_info = _get_user_info_from_graph(access_token)
            if user_info:
                session["user"].update(user_info)
        except Exception as e:
            print(f"Graph API hiba: {e}")
    
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        app_config.Config.AUTHORITY + "/oauth2/v2.0/logout" +
        "?post_logout_redirect_uri=" + url_for("index", _external=True)
    )

@app.route("/generate")
def generate_signature():
    if not session.get("user"):
        return redirect(url_for("login"))
    
    # Egyszerű szöveges aláírás generálása
    signature_text = _generate_text_signature(session["user"])
    
    return render_template('signature.html', 
                         signature_text=signature_text,
                         user=session["user"])

def _generate_text_signature(user_data):
    """Szöveges email aláírás generálása"""
    
    signature_lines = []
    
    # Név
    if user_data.get('name'):
        signature_lines.append(user_data['name'])
    
    # Beosztás
    if user_data.get('job_title'):
        signature_lines.append(user_data['job_title'])
    
    # Üres sor, ha van beosztás
    if user_data.get('job_title'):
        signature_lines.append("")
    
    # Cím
    if user_data.get('street_address'):
        signature_lines.append(user_data['street_address'])
    elif user_data.get('office_location'):
        signature_lines.append(user_data['office_location'])
    
    # Email
    if user_data.get('email'):
        signature_lines.append(f"Email: {user_data['email']}")
    
    # Telefon számok
    if user_data.get('mobile_phone'):
        signature_lines.append(f"Mobil: {user_data['mobile_phone']}")
    
    if user_data.get('business_phones') and len(user_data['business_phones']) > 0:
        phone = user_data['business_phones'][0]
        signature_lines.append(f"Telefon: {phone}")
    
    # Üres sor a végére
    signature_lines.append("")
    
    return "\n".join(signature_lines)

def _build_msal_app(cache=None):
    return msal.ConfidentialClientApplication(
        app_config.Config.CLIENT_ID,
        authority=app_config.Config.AUTHORITY,
        client_credential=app_config.Config.CLIENT_SECRET
    )

def _build_auth_url(authority=None, scopes=None, state=None):
    return _build_msal_app().get_authorization_request_url(
        scopes or [],
        state=state or str(uuid.uuid4()),
        redirect_uri=app_config.Config.REDIRECT_URI
    )

def _get_user_info_from_graph(access_token):
    """További felhasználói adatok lekérése Microsoft Graph API-ból"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Graph API endpoint a felhasználó részletes adataihoz
    graph_response = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers=headers,
        timeout=30
    )
    
    if graph_response.status_code == 200:
        user_data = graph_response.json()
        print("Graph API részletes adatok:", user_data)  # Debug információ
        return {
            "job_title": user_data.get("jobTitle"),
            "office_location": user_data.get("officeLocation"),
            "mobile_phone": user_data.get("mobilePhone"),
            "business_phones": user_data.get("businessPhones", []),
            "street_address": user_data.get("streetAddress")
        }
    return None

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=app_config.Config.PORT, debug=True)
