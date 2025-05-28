from flask import Flask, request, jsonify
import os
import json
import base64
from twilio.rest import Client
import firebase_admin
from firebase_admin import credentials, db

# Decode base64 and save to temp file
firebase_key_b64 = os.environ.get('FIREBASE_KEY_BASE64')
with open('/tmp/firebase_key.json', 'wb') as f:
    f.write(base64.b64decode(firebase_key_b64))

# Initialize Firebase
cred = credentials.Certificate('/tmp/firebase_key.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://emergency-module-1c979-default-rtdb.firebaseio.com/'
})

# Flask app init
app = Flask(__name__)

# Twilio credentials from env vars
account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
twilio_number = os.environ.get('TWILIO_PHONE_NUMBER')

# Twilio client
client = Client(account_sid, auth_token)

# Helper functions
def load_contacts(user_id):
    ref = db.reference(f'contacts/{user_id}')
    return ref.get() or {}

def save_contacts(user_id, data):
    ref = db.reference(f'contacts/{user_id}')
    ref.set(data)

def delete_contact(user_id, name):
    ref = db.reference(f'contacts/{user_id}/{name}')
    ref.delete()

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
    user_id = data.get("user_id")
    name = data.get("name")
    phone = data.get("phone")

    if not user_id or not name or not phone:
        return jsonify({"error": "user_id, name and phone are required"}), 400

    contacts = load_contacts(user_id)
    contacts[name] = phone
    save_contacts(user_id, contacts)

    return jsonify({"message": f"Contact {name} added successfully."})

@app.route("/get_contacts", methods=["POST"])
def get_contacts():
    data = request.get_json()
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    contacts = load_contacts(user_id)
    return jsonify({"contacts": contacts})

@app.route("/delete_contact", methods=["POST"])
def remove_contact():
    data = request.get_json()
    user_id = data.get("user_id")
    name = data.get("name")

    if not user_id or not name:
        return jsonify({"error": "user_id and name are required"}), 400

    delete_contact(user_id, name)
    return jsonify({"message": f"Contact {name} deleted successfully."})

@app.route("/send_alert", methods=["POST"])
def send_alert():
    data = request.get_json()
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    contacts = load_contacts(user_id)
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

# Run the app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
