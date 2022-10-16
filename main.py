# api https://docs.streamlit.io/library/api-reference

import streamlit as st
from streamlit_folium import st_folium
import requests
import json
import folium
from folium.plugins import MousePosition
import pandas as pd
import sklearn as sk
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import train_test_split
from patsy import dmatrices

st.title("Web app!")

# get api keys from .env file
with open("credentials.env", "r") as f:
  lines = [line.strip() for line in f.readlines()]
  api_keys = {}
  for line in lines:
    split = line.split(' ')
    api_keys[split[0]] = split[2]

AMBEE_API_KEY = api_keys['AMBEE_API_KEY']
MAP_API_KEY = api_keys['MAP_API_KEY']

AMBEE_URL = "https://api.ambeedata.com/weather/latest/by-lat-lng"
SOIL_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"


def display_info(lat, lng):

  ph, temperature, humidity = api_calls(lat, lng)

  try:
    crop_recommendations = crop_recommender_model(ph, temperature, humidity)
    st.write(crop_recommendations)
  except Exception as e:
    print(e)
    error = "Encountered error when training model or creating recommendation"
    st.write(error)


def api_calls(lat, lng):
  ambee_querystring = {"lat": lat, "lng": lng}
  soil_querystring = {
    "lat": lat,
    "lon": lng,
    'property': ['phh2o'],
    'depth': ['0-5cm'],
    'value': 'mean'
  }

  try:
    response = requests.get(SOIL_URL,
                            headers={'Content-type': "application/json"},
                            params=soil_querystring)
    soil_parsed = json.loads(response.text)
    ph = soil_parsed['properties']['layers'][0]['depths'][0]['values']['mean'] / 10
    st.write('PH:', ph)

  except Exception:
    soil_error = "No ph data for this region"
    st.write('Error:', soil_error)
    
  ambee_headers = {
    'x-api-key': AMBEE_API_KEY,
    'Content-type': "application/json"
  }

  try:
    response = requests.request("GET",
                                AMBEE_URL,
                                headers=ambee_headers,
                                params=ambee_querystring)
    ambee_parsed = json.loads(response.text)

    temperature = (ambee_parsed['data']['temperature'] - 32) * 5 / 9
    humidity = ambee_parsed['data']['humidity']
    st.write('Temperature:', temperature)
    st.write('Humidity:', humidity)

  except Exception:
    ambee_error = "No temperature and/or humidity data for this region"
    st.write('Error', ambee_error)

  return ph, temperature, humidity
  

def crop_recommender_model(ph, temp, humidity):
    df = pd.read_csv("Crop_recommendation.csv")
    X, y = matricies(df, ['ph', 'temperature', 'humidity'])
    model = KNeighborsClassifier(p=2)
    model.fit(X, y)
    return model.predict_proba([ph, temp, humidity])
    

def formula(args: list) -> str:
  return "C(label) ~ " + " + ".join(args)


def matricies(df, args: list):
  Y, X = dmatrices(formula(["0", *args]), df, return_type='dataframe')
  y = Y['label'].values
  return X, y


map_option, address_option, latlng_option = st.tabs(["Map", "Address", "Lat / Long"])

with map_option:
  m = folium.Map(zoom_start=20)
  formatter = "function(num) {return L.Util.formatNum(num, 3) + ' º ';};"

  MousePosition(position="topright",
                separator=" | ",
                empty_string="NaN",
                prefix="Coordinates:",
                lat_formatter=formatter,
                lng_formatter=formatter).add_to(m)

  m.add_child(folium.LatLngPopup())
  map = st_folium(m, height=350, width=700)

  if map['last_clicked']:
    lat, lng = map['last_clicked']['lat'], map['last_clicked']['lng']
    display_info(lat, lng)

with address_option:
  address = st.text_input('input address')

  if address:
    url = f"https://maps.googleapis.com/maps/api/place/autocomplete/" + \
      f"json?input={'%20'.join(address.split())}" + \
      f"&key={MAP_API_KEY}"

    resp = requests.request("GET", url)
    text = json.loads(resp.text)

    options = [i['description'] for i in text['predictions']]

    address = st.selectbox('suggestions', options)

    url = 'https://maps.googleapis.com/maps/api/geocode/json?address=' + \
      '%20'.join(address.split()) + \
      f"&key={MAP_API_KEY}"

    resp = requests.request("GET", url)
    text = json.loads(resp.text)

    try:
      latlng = text['results'][0]['geometry']['location']
      lat, lng = latlng['lat'], latlng['lng']

      m2 = folium.Map([lat, lng], zoom_start=15)
      folium.Marker([lat, lng]).add_to(m2)
      map2 = st_folium(m2, height=350, width=700)

      display_info(lat, lng)

    except IndexError:
      print('lat lng not found')

def check_lat_lng(lat, lng):
  try:
    lat = float(lat)
    lng = float(lng)
  except ValueError:
    return False

  if lat < -90 or lat > 90:
    return False

  if lng < -180 or lng > -180:
    return False

  return True


with latlng_option:
  col1, col2 = st.columns(2)
  with col1:
    lat = st.text_input('input lat')
  with col2:
    lng = st.text_input('input lng')

  if lat and lng:
    if not check_lat_lng(lat, lng):
      st.write('invalid values - try again')
    else:
      m3 = folium.Map([lat, lng], zoom_start=15)
      folium.Marker([lat, lng]).add_to(m3)
      map3 = st_folium(m3, height=350, width=700)

      display_info(lat, lng)
