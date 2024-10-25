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

class NormalesMitgliedForm(FlaskForm):
    ermaessigt = BooleanField("""Ermäßigter Beitrag %TAG% - Für Schüler*innen, Studierende,
            Auszubildende, Empfänger*innen
            von Sozial- oder Bürgergeld einschließlich Leistungen nach § 22 ohne
            Zuschläge oder nach § 24 des zweiten Sozialgesetzbuchs (SGB II) sowie
            Empfänger*innen von Ausbildungsförderung nach dem
            Bundesausbildungsförderungsgesetz (BAföG)""")
    werkstatt = BooleanField("Werkstattnutzung %TAG%")

class SEPABase(FlaskForm):
    mitglied_is_inhabende = BooleanField("Mitglied ist kontoinhabende Person", default="checked")
    einwilligung = BooleanField("""Hiermit ermächtige ich den LeineLab e.V., wiederkehrende Zahlungen von
        meinem Konto mittels Lastschrift einzuziehen. Zugleich weise ich mein Kreditinstitut an,
        die vom LeineLab e.V. auf mein Konto gezogenen Lastschriften einzulösen.
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
    foerderbeitrag = DecimalRangeField("", default=10, render_kw={"min": 2.5, "step": 2.5, "max": 30})

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
    mitgliedsart = RadioField('Mitgliedsart', default="Normale Mitgliedschaft", choices=["Normale Mitgliedschaft", "Fördermitgliedschaft (Kein Stimmrecht auf Mitgliederversammlungen, keine Werkstattnutzung, keine Schließberechtigung, beliebiger Beitrag)"])

    datenschutz = BooleanField("""Ich stimme zu, dass meine Stammdaten im 
        Rahmen der Datenschutzvereinbarung auf der Webseite des LeineLab e.V. verarbeitet
        werden.""", [InputRequired("Zustimmung ist erforderlich.")])

def calc_beitrag(ermaessigt, werkstatt, foerderbeitrag=None):
    if foerderbeitrag:
        return foerderbeitrag

    if ermaessigt:
        if werkstatt:
            return 10
        else:
            return 2.5
    else:
        if werkstatt:
            return 28
        else:
            return 10


@app.route("/", methods=["GET", "POST"])
def home():
    xCls = NormalesMitgliedForm

    if request.form.get('mitgliedsart') == "Fördermitgliedschaft (Kein Stimmrecht auf Mitgliederversammlungen, keine Werkstattnutzung, keine Schließberechtigung, beliebiger Beitrag)":
        #form = BaseFormFoerderMitglied()
        xCls = FoerderMitgliedForm

    sepaCls = SEPAAbweichendeInhabende
    if request.form.get("sepa-mitglied_is_inhabende"):
        sepaCls = SEPASameInhabende

    class MyForm(BaseForm):
        x = FormField(xCls)
        sepa = FormField(sepaCls)

    form = MyForm()

    if xCls == NormalesMitgliedForm:
        ermaessigt = form.x.ermaessigt.data
        werkstatt = form.x.werkstatt.data

        tag = ''
        if not ermaessigt:
            tag = '<span class="badge rounded-pill bg-success">%.2f €</span>' % (calc_beitrag(True, werkstatt)-calc_beitrag(False, werkstatt))
        
        form.x.ermaessigt.label.text = form.x.ermaessigt.label.text.replace("%TAG%", tag)

        tag = ''
        if not werkstatt:
            tag = '<span class="badge rounded-pill bg-info text-dark">%+.2f €</span>' % (calc_beitrag(ermaessigt, True)-calc_beitrag(ermaessigt, False))
        
        form.x.werkstatt.label.text = form.x.werkstatt.label.text.replace("%TAG%", tag)

    if sepaCls == SEPASameInhabende:
        form.sepa.kontoinhabende.process_data(form.data['name'])
        form.sepa.kontoinhabende_addresse.process_data(form.data['full_address'])


    foerderbeitrag = None
    werkstatt = request.form.get("x-werkstatt")
    ermaessigt = request.form.get("x-ermaessigt")

    if request.form.get("mitgliedsart") == "Fördermitgliedschaft (Kein Stimmrecht auf Mitgliederversammlungen, keine Werkstattnutzung, keine Schließberechtigung, beliebiger Beitrag)":
        foerderbeitrag = request.form.get("x-foerderbeitrag", 10)

    beitrag = calc_beitrag(ermaessigt, werkstatt, foerderbeitrag)

    if form.validate_on_submit() and "HX-Target" in request.headers and request.headers['HX-Target'] == 'form':
        msg = Message(subject=f'Neue Mitgliedsanfrage von {form.data["name"]}!', sender='root@leinelab.org', recipients=['vorstand@leinelab.org'])
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
