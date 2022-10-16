# api https://docs.streamlit.io/library/api-reference

import streamlit as st
from streamlit_folium import st_folium
import requests
import json
import folium
from folium.plugins import MousePosition

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


def display_lat_lng(lat, lng):
  ambee_querystring = {"lat": lat, "lng": lng}
  soil_querystring = {
    "lat": lat,
    "lng": lng,
    'property': ['nitrogen', 'phh2o'],
    'depth': ['0-5cm']
  }

  response = requests.get(SOIL_URL,
                          headers={'Content-type': "application/json"},
                          params=soil_querystring)
  st.write(response.text)

  ambee_headers = {
    'x-api-key': AMBEE_API_KEY,
    'Content-type': "application/json"
  }
  response = requests.request("GET",
                              AMBEE_URL,
                              headers=ambee_headers,
                              params=ambee_querystring)
  parsed = json.loads(response.text)

  temperature = parsed['data']['temperature']
  humidity = parsed['data']['humidity']
  st.write('Temperature:', temperature)
  st.write('Humidity:', humidity)


map_option, address_option, latlng_option = st.tabs(
  ["map", "address", "lat/lng"])

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
    display_lat_lng(lat, lng)

with address_option:
  address = st.text_input('input address')
  #address = '716 W 35th St, Austin, TX 78705'

  if address:
    url = 'https://maps.googleapis.com/maps/api/geocode/json?address='
    url += '%20'.join(address.split())
    url += '&key=AIzaSyAuxFDYZAEeHxmQXRMm5ciVG7CJae7iuKA'

    resp = requests.request("GET", url)
    text = json.loads(resp.text)

    try:
      latlng = text['results'][0]['geometry']['location']
      lat, lng = latlng['lat'], latlng['lng']

      m2 = folium.Map([lat, lng], zoom_start=15)
      map2 = st_folium(m2, height=350, width=700)

      display_lat_lng(lat, lng)

    except IndexError:
      print('lat lng not found')

with latlng_option:
  col1, col2 = st.columns(2)
  with col1:
    lat = st.text_input('input lat')
  with col2:
    lng = st.text_input('input lng')

  if lat and lng:
    # TODO add check for numbers, range

    m3 = folium.Map([lat, lng], zoom_start=15)
    map3 = st_folium(m3, height=350, width=700)

    display_lat_lng(lat, lng)