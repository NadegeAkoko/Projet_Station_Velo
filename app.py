import requests
import pandas as pd
import mysql.connector
from flask import Flask, render_template, jsonify
import sys

print(f"Python utilisé : {sys.executable}")

# Configuration de la base de données
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Nadine@1997.",
    "database": "velo_station"
}

# Clé API et contrat pour JCDecaux
API_KEY = "4086aea31c8417cb8d6d6fb414bf19dde3722c32"
CONTRACT = "PARIS"  # Ville de Lille
BASE_URL = f"https://api.jcdecaux.com/vls/v1/stations?contract={CONTRACT}&apiKey={API_KEY}"

# Fonction pour récupérer les données des stations depuis l'API JCDecaux
def fetch_bike_station_data():
    stations = []
    try:
        # Récupérer les données depuis l'API JCDecaux
        response = requests.get(BASE_URL)
        response.raise_for_status()  # Vérifier que la requête a réussi
        data = response.json()

        # Vérifier la structure de la réponse
        print(data)  # Afficher les données pour examiner la structure

        if not data:
            print("Aucune station trouvée pour Lille. Vérifie le contrat de la ville.")
            return pd.DataFrame()

        # Traitement des stations
        for station in data:
            stations.append({
                "id_station": station.get("number"),
                "commune": station.get("name"),
                "nb_places_dispo": station.get("available_bikes", 0),  # Assure-toi que 'available_bikes' est correct
                "longitude": station["position"]["lng"],
                "latitude": station["position"]["lat"],
            })
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération des données : {e}")
        return pd.DataFrame()

    return pd.DataFrame(stations)

# Connexion à la base de données
def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as e:
        print(f"Erreur MySQL : {e}")
        return None

# Création de la table si elle n'existe pas
def create_table():
    connection = get_db_connection()
    if not connection:
        return
    create_table_query = """
    CREATE TABLE IF NOT EXISTS stations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_station VARCHAR(50) UNIQUE,
        commune VARCHAR(100),
        nb_places_dispo INT,
        longitude FLOAT,
        latitude FLOAT
    );
    """
    try:
        cursor = connection.cursor()
        cursor.execute(create_table_query)
        connection.commit()
    except mysql.connector.Error as e:
        print(f"Erreur lors de la création de la table : {e}")
    finally:
        cursor.close()
        connection.close()

# Insertion des données dans la base de données
def insert_stations_data(df):
    connection = get_db_connection()
    if not connection:
        return
    insert_query = """
    INSERT IGNORE INTO stations (id_station, commune, nb_places_dispo, longitude, latitude)
    VALUES (%s, %s, %s, %s, %s)
    """
    data_to_insert = df[["id_station", "commune", "nb_places_dispo", "longitude", "latitude"]].values.tolist()
    try:
        cursor = connection.cursor()
        cursor.executemany(insert_query, data_to_insert)
        connection.commit()
        print(f"{cursor.rowcount} lignes insérées.")
    except mysql.connector.Error as e:
        print(f"Erreur MySQL : {e}")
    finally:
        cursor.close()
        connection.close()

# Flask application
app = Flask(__name__)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/get_stations')
def get_stations():
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Erreur de connexion à la base de données"})
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM stations")
        stations = cursor.fetchall()
        return jsonify(stations)
    except mysql.connector.Error as e:
        print(f"Erreur MySQL : {e}")
        return jsonify({"error": "Erreur lors de la récupération des données"})
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    create_table()

    # Récupérer et insérer les données des stations JCDecaux
    df_jcdecaux = fetch_bike_station_data()
    if not df_jcdecaux.empty:
        insert_stations_data(df_jcdecaux)

    app.run(debug=True)
