import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from htmx_components_flask import htmx_components_flask

app = Flask(__name__)

csrf = CSRFProtect(app)
csrf.init_app(app)

if not os.path.exists("SECRET_KEY"):
    import secrets;
    with open("SECRET_KEY", "w") as f:
        f.write(secrets.token_hex() + "\n")

with open("SECRET_KEY") as f:
    SECRET_KEY = f.read().strip()

app.config.update(
    SECRET_KEY=SECRET_KEY
)

app.register_blueprint(htmx_components_flask)

from app import views
