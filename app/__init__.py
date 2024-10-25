import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from htmx_components_flask import htmx_components_flask
from flask_mail import Mail
from . import config

app = Flask(__name__)

if not os.path.exists("SECRET_KEY"):
    import secrets;
    with open("SECRET_KEY", "w") as f:
        f.write(secrets.token_hex() + "\n")

with open("SECRET_KEY") as f:
    SECRET_KEY = f.read().strip()

app.config.from_object(config.Config)

app.config.update(
    SECRET_KEY=SECRET_KEY
)

csrf = CSRFProtect(app)
csrf.init_app(app)

mail = Mail(app)

print("Using mailserver: " + app.config["MAIL_SERVER"])

from app import views
