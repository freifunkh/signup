from app import app
from flask import render_template, request, jsonify

@app.route("/", methods=["GET"])
def home():
    b = beitrag()
    return render_template("index.html",form=request.form, beitrag=b)

@app.route("/beitragstuff", methods=["POST"])
def beitragsstuff():
    b = beitrag()

    return render_template(
        "partials/beitragsstuff.html",
        form=request.form,
        beitrag=b)

@app.route("/sepa", methods=["POST"])
def sepa():
    return render_template(
        "partials/sepa.html",
        form=request.form)

@app.route("/beitrag", methods=["POST"])
def beitrag():
    if request.form.get("mitgliedschaftsart") == "foerder":
        return request.form.get("foerderbeitrag", "10") + " €"

    if request.form.get("ermaessigt"):
        if request.form.get("werkstatt"):
            return "10 €"
        else:
            return "2,50 €"

    if request.form.get("werkstatt"):
        return "28 €"

    return "10 €"

@app.route("/submit", methods=["POST"])
def submit():
    return NotImplemented
