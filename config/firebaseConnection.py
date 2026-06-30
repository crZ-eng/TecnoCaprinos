import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"))

def initialize_firebase():

    if firebase_admin._apps:
        return firestore.client()

    try:

        file_name = os.getenv("FIREBASE_KEYS_PATH")

        if not file_name:
            raise Exception(
                "No existe FIREBASE_KEYS_PATH dentro del archivo .env"
            )

        cert_path = os.path.join(BASE_DIR, file_name)

        if not os.path.exists(cert_path):
            raise FileNotFoundError(
                f"No existe el archivo:\n{cert_path}"
            )

        cred = credentials.Certificate(cert_path)

        firebase_admin.initialize_app(cred)

        print("✅ Firebase inicializado correctamente")

        return firestore.client()

    except Exception as e:

        print(f"❌ Error Firebase: {e}")

        return None