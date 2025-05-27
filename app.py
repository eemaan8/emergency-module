from flask import Flask, request, jsonify
import os
import json
from twilio.rest import Client
import firebase_admin
from firebase_admin import credentials, db

# Flask app init
app = Flask(__name__)

# Twilio credentials from env vars
account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
twilio_number = os.environ.get('TWILIO_PHONE_NUMBER')

# Twilio client
client = Client(account_sid, auth_token)

# Firebase credentials (service account .json)
firebase_cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(firebase_cred, {
    'databaseURL': 'https://emergency-module-1c979-default-rtdb.firebaseio.com/'  # 🔁 Replace this with your actual URL
})

# Firebase contact helpers
def load_contacts():
    ref = db.reference('contacts')
    return ref.get() or {}

def save_contacts(data):
    ref = db.reference('contacts')
    ref.set(data)

# Send SMS function
def send_sms(to_number, message):
    message = client.messages.create(
        body=message,
        from_=twilio_number,
        to=to_number
    )
    print(f"SMS sent to {to_number}, SID: {message.sid}")

# Routes
@app.route("/")
def home():
    return "Emergency Contact API is running with Firebase!"

@app.route("/add_contact", methods=["POST"])
def add_contact():
    data = request.get_json()
    name = data.get("name")
    phone = data.get("phone")

    if not name or not phone:
        return jsonify({"error": "Name and phone are required"}), 400

    contacts = load_contacts()
    contacts[name] = phone
    save_contacts(contacts)

    return jsonify({"message": f"Contact {name} added successfully."})

@app.route("/get_contacts", methods=["GET"])
def get_contacts():
    contacts = load_contacts()
    return jsonify({"contacts": contacts})

@app.route("/send_alert", methods=["POST"])
def send_alert():
    contacts = load_contacts()
    if not contacts:
        return jsonify({"error": "No contacts found."}), 404

    alert_message = "🚨 Emergency Alert: Your contact needs immediate help!"

    sent_to = []
    errors = []

    for name, phone in contacts.items():
        try:
            send_sms(phone, alert_message)
            sent_to.append(name)
        except Exception as e:
            errors.append({"name": name, "phone": phone, "error": str(e)})

    response = {"message": "Alert sent to contacts", "sent_to": sent_to}
    if errors:
        response["errors"] = errors

    return jsonify(response)

# For Render.com port setup
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
