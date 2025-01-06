from app import app, mail
from lxml import etree, html
from flask import render_template, request, jsonify, redirect, make_response,after_this_request
from flask_wtf import FlaskForm
from wtforms import StringField, validators, RadioField, FormField, BooleanField, DecimalRangeField
from wtforms.validators import DataRequired, Regexp, ValidationError, Length, InputRequired
from schwifty import IBAN
from flask_mail import Message, Mail

# Custom IBAN validator
def iban_validator(form, field):
    iban_value = field.data
    try:
        IBAN(iban_value)
    except ValueError:
        raise ValidationError('Ungültige IBAN.')

parser = etree.HTMLParser(encoding="utf-8")

class AktivesMitgliedForm(FlaskForm):
    pass

class SEPABase(FlaskForm):
    mitglied_is_inhabende = BooleanField("Mitglied ist kontoinhabende Person", default="checked")
    einwilligung = BooleanField("""Hiermit ermächtige ich den FNorden e.V., wiederkehrende Zahlungen von
        meinem Konto mittels Lastschrift einzuziehen. Zugleich weise ich mein Kreditinstitut an,
        die vom FNorden e.V. auf mein Konto gezogenen Lastschriften einzulösen.
        """, [validators.InputRequired("Zustimmung ist erforderlich.")])
    iban = StringField('IBAN', [iban_validator])
    kreditinstitut = StringField('Kreditinstitut', [Length(min=3, message="Der Name des Kreditinstituts sollte mindestens 3 Zeichen haben.")])

class SEPASameInhabende(SEPABase):
    kontoinhabende = StringField('Kontoinhabende Person', render_kw={"disabled": ""})
    kontoinhabende_addresse = StringField('Adresse (Straße Hausnummer, PLZ Stadt)', render_kw={"disabled": ""})

class SEPAAbweichendeInhabende(SEPABase):
    kontoinhabende = StringField('Kontoinhabende Person(en)', validators=[
        DataRequired("Bitte gebe den Namen der kontoinhabenden Person(en) an.")
    ])
    kontoinhabende_addresse = StringField('Adresse (Straße Hausnummer, PLZ Stadt)', [
        DataRequired(message="Bitte gebe deine Adresse ein."),
        Regexp(r'^[\w\s.-]+\s\d{1,4}[a-z]*,\s\d{5}\s[\w\s.-]+$', message="Bitte geben Sie eine gültige Adresse im Format 'Straße Hausnummer, PLZ Stadt' ein.")
    ])

class FoerderMitgliedForm(FlaskForm):
    foerderbeitrag = DecimalRangeField("", default=10, render_kw={"min": 5, "step": 2.5, "max": 30})

class BaseForm(FlaskForm):
    name = StringField('Name', validators=[
        DataRequired("Bitte gebe deinen Namen ein.")
    ])
    full_address = StringField('Adresse (Straße Hausnummer, PLZ Stadt)', [
        DataRequired(message="Bitte gebe deine Adresse ein."),
        Regexp(r'^[\w\s.-]+\s\d{1,4}[a-z]*,\s\d{5}\s[\w\s.-]+$', message="Bitte geben Sie eine gültige Adresse im Format 'Straße Hausnummer, PLZ Stadt' ein.")
    ])
    email = StringField('Email', [
        validators.Length(min=6, message='Ein bisschen kurz für eine EMail-Adresse?'),
        validators.Email(message='Keine valide EMail-Adresse.')
    ])
    mitgliedsart = RadioField('Mitgliedsart', default="Fördermitgliedschaft (Kein Stimmrecht auf Mitgliederversammlungen, beliebiger Beitrag)", choices=["Aktive Mitgliedschaft (fortwährende Teilnahme an Mitgliederversammlungen wird erwartet, um Stimmrecht auszuüben)", "Fördermitgliedschaft (Kein Stimmrecht auf Mitgliederversammlungen, beliebiger Beitrag)"])

    datenschutz = BooleanField("""Ich stimme zu, dass meine Stammdaten im 
        Rahmen der Datenschutzvereinbarung auf der Webseite des FNorden e.V. verarbeitet
        werden.""", [InputRequired("Zustimmung ist erforderlich.")])

def calc_beitrag(foerderbeitrag=None):
    if foerderbeitrag:
        return foerderbeitrag
    return 5.0

@app.route("/", methods=["GET", "POST"])
def home():
    xCls = AktivesMitgliedForm

    if request.form.get('mitgliedsart') == "Fördermitgliedschaft (Kein Stimmrecht auf Mitgliederversammlungen, beliebiger Beitrag)":
        #form = BaseFormFoerderMitglied()
        xCls = FoerderMitgliedForm

    sepaCls = SEPAAbweichendeInhabende
    if request.form.get("sepa-mitglied_is_inhabende"):
        sepaCls = SEPASameInhabende

    class MyForm(BaseForm):
        x = FormField(xCls)
        sepa = FormField(sepaCls)

    form = MyForm()

    if sepaCls == SEPASameInhabende:
        form.sepa.kontoinhabende.process_data(form.data['name'])
        form.sepa.kontoinhabende_addresse.process_data(form.data['full_address'])


    foerderbeitrag = None

    if request.form.get("mitgliedsart") == "Fördermitgliedschaft (Kein Stimmrecht auf Mitgliederversammlungen, beliebiger Beitrag)":
        foerderbeitrag = request.form.get("x-foerderbeitrag", 10)

    beitrag = calc_beitrag(foerderbeitrag)

    if form.validate_on_submit() and "HX-Target" in request.headers and request.headers['HX-Target'] == 'form':
        msg = Message(subject=f'Neue Mitgliedsanfrage von {form.data["name"]}!', sender='jan-niklas@fnorden.de', recipients=['jan-niklas@fnorden.de'])
        msg.body = render_template("mail.txt", form=form, beitrag=beitrag)
        print(msg)
        mail.send(msg)
        print("redirect")

        @after_this_request
        def add_header(response):
            response.headers['HX-Redirect'] = "/success"
            return response

        return "Success"

    @after_this_request
    def add_header(response):
        if "HX-Request" in request.headers and response.status_code == 200:
            data = response.get_data()
            tree = html.fromstring(data, parser=parser)
            target = request.headers["HX-Target"]
            target_elems = tree.xpath(f"//*[@id='{target}']")
            if len(target_elems) > 0:
                oob_elems = tree.xpath("//*[@hx-swap-oob]")
                elems = [target_elems[0]] + oob_elems
                response.data = "".join([html.tostring(elem, encoding=str) for elem in elems])

        return response

    return render_template("index.html", form=form, beitrag=beitrag)

@app.errorhandler(Exception)
def handle_exception(e):
    response = make_response('<div class="alert alert-danger" role="alert">ERROR!!<br><br>' + str(e) + "</div>", 200)
    return response

@app.route("/success", methods=["GET"])
def sucess():
    return render_template("success.html")
