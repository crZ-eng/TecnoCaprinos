import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

def initialize_firebase():
    if not firebase_admin._apps:
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))

            file_name = os.getenv('FIREBASE_KEYS_PATH')
            cert_path = os.path.join(base_dir, file_name)

            if not os.path.exists(cert_path):
                raise FileNotFoundError(f" ❌ No se encontró el archivo en: {cert_path}")

            cred = credentials.Certificate(cert_path)
            firebase_admin.initialize_app(cred)
            print(f" 👌 Firebase SDK inicializado con ruta absoluta")
        except Exception as e:
            print(f" ❌ Error al inicializar Firebase: {e}")
            return None
    return firestore.client()