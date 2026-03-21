import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN      = os.environ.get("VERIFY_TOKEN")
RASA_SERVER_URL   = os.environ.get("RASA_SERVER_URL", "http://localhost:5005")


@app.route("/webhook", methods=["GET"])
def verify():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Token invalide", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                sender_id = event["sender"]["id"]
                if "message" in event:
                    texte = event["message"].get("text", "")
                    if texte:
                        reponses = appeler_rasa(sender_id, texte)
                        for rep in reponses:
                            envoyer_message(sender_id, rep)
    return jsonify({"status": "ok"}), 200


def appeler_rasa(sender_id: str, texte: str) -> list:
    """Appelle le serveur Rasa et retourne la liste des réponses."""
    try:
        r = requests.post(
            f"{RASA_SERVER_URL}/webhooks/rest/webhook",
            json={"sender": sender_id, "message": texte},
            timeout=10,
        )
        reponses = r.json()  # liste de {"recipient_id": ..., "text": ...}
        return [rep["text"] for rep in reponses if "text" in rep]
    except Exception as e:
        print(f"Erreur Rasa : {e}")
        return ["Désolé, une erreur est survenue."]


def envoyer_message(recipient_id: str, texte: str):
    url = "https://graph.facebook.com/v19.0/me/messages"
    r = requests.post(
        url,
        json={"recipient": {"id": recipient_id}, "message": {"text": texte}},
        params={"access_token": PAGE_ACCESS_TOKEN},
    )
    if r.status_code != 200:
        print(f"Erreur envoi : {r.status_code} — {r.text}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
