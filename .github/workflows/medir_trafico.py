from datetime import datetime
import json
import os
import gspread
import requests

# 1. Configuración desde las variables secretas de GitHub
API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

# Cargar las credenciales de Google Sheets desde el secreto de GitHub
credentials_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS_JSON"))

# 2. Configuración de Google Sheets
SPREADSHEET_ID = "1c2wbSOkc0Uh5UU3kpUMyBlxUrxqY5zoeMT3LfXTLFRA"

URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
HEADERS = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": API_KEY,
    "X-Goog-FieldMask": "routes.duration,routes.staticDuration,routes.distanceMeters",
}

TRAMOS = [
    {
        "calle": "Antonio Plaza (Norte a Sur)",
        "origen": [20.542918, -100.692304],
        "destino": [20.541905, -100.692781],
    },
    {
        "calle": "Guadalupe Victoria - Elektra (Oeste a Este)",
        "origen": [20.5455447, -100.6883712],
        "destino": [20.5458349, -100.6882553],
    },
    {
        "calle": "Jesús Cabrera M. - Oxxo hacia Gasolinera Repsol",
        "origen": [20.5454678, -100.6928596],
        "destino": [20.5444972, -100.6925254],
    },
    {
        "calle": "Juan Aldama - Puente Colorado",
        "origen": [20.547217, -100.686691],
        "destino": [20.547793, -100.686370],
    },
    {
        "calle": "Mariano Matamoros - Presidencia (Sur a Norte)",
        "origen": [20.5445226, -100.6886947],
        "destino": [20.5448155, -100.6889376],
    },
    {
        "calle": "Melchor Ocampo - Sanatorio Macias",
        "origen": [20.5472575, -100.6886914],
        "destino": [20.5465525, -100.689026],
    },
    {
        "calle": "Morelos - Semáforo Lienzo Charro",
        "origen": [20.543051, -100.6777473],
        "destino": [20.5432212, -100.6783004],
    },
    {
        "calle": "Narciso Mendoza - Libros Rocío",
        "origen": [20.5484064, -100.6873489],
        "destino": [20.5481101, -100.686584],
    },
    {
        "calle": "Narciso Mendoza - Semáforo (Hacia Poniente)",
        "origen": [20.5475831, -100.6842762],
        "destino": [20.5479461, -100.6858744],
    },
    {
        "calle": "Octaviano Muñoz Ledo - Los Charcos",
        "origen": [20.5480496, -100.6892046],
        "destino": [20.5482068, -100.6897043],
    },
    {
        "calle": "Pípila - Mercado (Sur a Norte)",
        "origen": [20.5456148, -100.6915668],
        "destino": [20.5467076, -100.6909783],
    },
    {
        "calle": "Piña Soria - Auto Zone (Hacia Este)",
        "origen": [20.5420509, -100.6915272],
        "destino": [20.5416476, -100.6925724],
    },
    {
        "calle": "Vicente Ruiz - Aurrerá (Sur a Norte)",
        "origen": [20.5472582, -100.6906872],
        "destino": [20.5481896, -100.6902459],
    },
]


def consultar_tramo(origen, destino):
  body = {
      "origin": {
          "location": {
              "latLng": {"latitude": origen[0], "longitude": origen[1]}
          }
      },
      "destination": {
          "location": {
              "latLng": {"latitude": destino[0], "longitude": destino[1]}
          }
      },
      "travelMode": "DRIVE",
      "routingPreference": "TRAFFIC_AWARE",
  }

  resp = requests.post(URL, json=body, headers=HEADERS)
  if resp.status_code != 200:
    return None, f"Error {resp.status_code}: {resp.text}"

  data = resp.json()
  if "routes" not in data or not data["routes"]:
    return None, "No se encontró ruta"

  ruta = data["routes"][0]
  distancia_m = ruta.get("distanceMeters", 0)
  tiempo_real_s = int(ruta.get("duration", "0s").replace("s", ""))
  tiempo_base_s = int(ruta.get("staticDuration", "0s").replace("s", ""))
  retraso_s = max(0, tiempo_real_s - tiempo_base_s)
  pct_congestion = (
      (retraso_s / tiempo_base_s) * 100 if tiempo_base_s > 0 else 0.0
  )

  return {
      "distancia_m": distancia_m,
      "tiempo_base_s": tiempo_base_s,
      "tiempo_real_s": tiempo_real_s,
      "retraso_s": retraso_s,
      "pct_congestion": round(pct_congestion, 2),
  }, None


def main():
  fecha_actual = datetime.now().strftime("%Y-%m-%d")
  hora_actual = datetime.now().strftime("%H:%M:%S")

  # Conexión usando el diccionario seguro cargado desde GitHub Secrets
  gc = gspread.service_account_from_dict(credentials_dict)
  sheet = gc.open_by_key(SPREADSHEET_ID).sheet1

  filas_nuevas = []

  for tramo in TRAMOS:
    res, err = consultar_tramo(tramo["origen"], tramo["destino"])
    if err:
      continue

    filas_nuevas.append([
        fecha_actual,
        hora_actual,
        tramo["calle"],
        res["distancia_m"],
        res["tiempo_base_s"],
        res["tiempo_real_s"],
        res["retraso_s"],
        res["pct_congestion"],
    ])

  if filas_nuevas:
    sheet.append_rows(filas_nuevas)
    print("¡Monitoreo completado y registrado con éxito en la nube!")


if __name__ == "__main__":
  main()