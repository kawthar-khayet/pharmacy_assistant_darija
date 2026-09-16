"""Interactive terminal client for the pharmacy-assistant API.

Usage:
    python api/chat_cli.py
    (tape ta question en darija/arabe/francais, Ctrl+C ou "quit" pour sortir)

Maintains one session_id for the whole run, so a follow-up answer (e.g.
just a city name, after the bot asked "dans quelle ville ?") is understood
as a continuation of the previous question rather than a new, unrelated one.

When the bot is waiting for a city/neighborhood, the generic "Toi >" prompt
is replaced by a dedicated "Ville/quartier >" prompt, and nothing is
printed until that sub-exchange is resolved -- so the flow reads as one
continuous question/answer instead of two separate bot replies.

Requires the API server to be running (uvicorn api.main:app --port 8001).
"""
import sys
import uuid

import requests

API_URL = "http://127.0.0.1:8001/chat"


def send(text: str, session_id: str) -> dict:
    resp = requests.post(API_URL, json={"text": text, "session_id": session_id}, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    session_id = str(uuid.uuid4())
    print("Assistant Pharmacie - tape ta question (darija/arabe/francais), 'quit' pour sortir\n")

    while True:
        try:
            text = input("Toi > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAu revoir.")
            break

        if not text:
            continue
        if text.lower() in {"quit", "exit", "q"}:
            print("Au revoir.")
            break

        try:
            data = send(text, session_id)
        except requests.ConnectionError:
            print("Erreur : impossible de joindre l'API. Le serveur tourne-t-il ? "
                  "(uvicorn api.main:app --port 8001)")
            continue
        except requests.HTTPError as e:
            print(f"Erreur API : {e}")
            continue

        session_id = data["session_id"]

        # Slot-filling sub-dialogue: keep asking via the dedicated prompt
        # until the bot has what it needs, then print its final reply once.
        while data.get("awaiting_localisation"):
            try:
                location = input("Ville/quartier > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nAu revoir.")
                return
            if not location:
                continue
            try:
                data = send(location, session_id)
            except (requests.ConnectionError, requests.HTTPError) as e:
                print(f"Erreur API : {e}")
                break
            session_id = data["session_id"]

        print(f"\nBot > {data['reply']}\n")


if __name__ == "__main__":
    main()
