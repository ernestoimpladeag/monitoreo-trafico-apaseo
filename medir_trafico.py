from datetime import datetime, time
import json
import os
from zoneinfo import ZoneInfo
import gspread
import requests

API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
credentials_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS_JSON"))
SPREADSHEET_ID = "1c2wbSOkc0Uh5UU3kpUMyBlxUrxqY5zoeMT3LfXTLFRA"

URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
HEADERS = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": API_KEY,
    "X-Goog-FieldMask": "routes.duration,routes.staticDuration,routes.distanceMeters",
}

# Lista de tramos actualizada
TRAMOS = [
    {
        "calle": "ANTONIO PLAZA (NORTE A SUR)",
        "origen": [20.542918, -100.692304],
        "destino": [20.541905, -100.692781],
    },
    {
        "calle": "Guadalupe Victoria - Elektra (Oeste a Este)",
        "origen": [20.546089, -100.688960],
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
        "origen": [20.54439663335955, -100.68874870809661],
        "destino": [20.54523874876236, -100.68835288044802],
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
        "calle": "Narciso Mendoza - Hacia Oriente (Puente Colorado)",
        "origen": [20.5484064, -100.6873489],
        "destino": [20.5481101, -100.686584],
    },
    {
        "calle": "Narciso Mendoza - Semáforo (Hacia Poniente)",
        "origen": [20.5475831, -100.6842762],
        "destino": [20.54808261075303, -100.68639940430883],
    },
    {
        "calle": "Octaviano Muñoz Ledo - Los Charcos (Este a Oeste)",
        "origen": [20.5480496, -100.6892046],
        "destino": [20.54840359697561, -100.68989595617006],
    },
    {
        "calle": "Pípila - Mercado (Sur a Norte)",
        "origen": [20.5456148, -100.6915668],
        "destino": [20.5482068, -100.6897043],
    },
    {
        "calle": "Piña Soria - Auto Zone (Hacia Este / Salida Qro)",
        "origen": [20.5420509, -100.6915272],
        "destino": [20.5416476, -100.6925724],
    },
    {
        "calle": "Vicente Ruiz - Aurrerá (Sur a Norte)",
        "origen": [20.5472582, -100.6906872],
        "destino": [20.5481896, -100.6902459],
    },
]


def es_horario_permitido(ahora_mexico):
  dia_semana = ahora_mexico.weekday()  # 0 a 4 = Lunes a Viernes, 5-6 = Fines
  hora_actual = ahora_mexico.time()

  if dia_semana < 5:  # Lunes a Viernes
    r1_ini, r1_fin = time(6, 40), time(8, 20)
    r2_ini, r2_fin = time(12, 40), time(14, 40)
    r3_ini, r3_fin = time(18, 20), time(20, 20)
    return (
        (r1_ini <= hora_actual <= r1_fin)
        or (r2_ini <= hora_actual <= r2_fin)
        or (r3_ini <= hora_actual <= r3_fin)
    )
  else:  # Sábado y Domingo
    r_ini, r_fin = time(11, 0), time(15, 20)
    return r_ini <= hora_actual <= r_fin


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

  # Porcentaje de retraso real (ej. si hay 10s de retraso sobre 20s base, da 50.0%)
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
  zona_mexico = ZoneInfo("America/Mexico_City")
  ahora_mexico = datetime.now(zona_mexico)

  # Validación estricta de horario en México
  if not es_horario_permitido(ahora_mexico):
    print(f"Fuera de horario ({ahora_mexico.strftime('%H:%M:%S')}), omitiendo.")
    return

  fecha_actual = ahora_mexico.strftime("%Y-%m-%d")
  hora_actual = ahora_mexico.strftime("%H:%M:%S")

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
    print("¡Monitoreo actualizado y registrado con éxito!")


if __name__ == "__main__":
  main()
