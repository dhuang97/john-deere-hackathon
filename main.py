# api https://docs.streamlit.io/library/api-reference

from dotenv import load_dotenv
import os

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


load_dotenv('credentials.env')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
AMBEE_API_KEY = os.getenv('AMBEE_API_KEY')


AMBEE_URL = "https://api.ambeedata.com/weather/latest/by-lat-lng"
SOIL_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
ZOOM_LEVEL = 15


st.title("Title placeholder")



def format_float(f):
    return round(f, 2)

def request(url, headers=None, params=None):
    return requests.get(url, headers=headers, params=params)

def parse_response(resp):
    return json.loads(resp.text)

def valid_lat_lng(lat, lng):
    try:
        lat = float(lat)
        lng = float(lng)
    except ValueError:
        return False

    if lat < -90 or lat > 90:
        return False

    if lng < -180 or lng > 180:
        return False

    return True


def display_info(lat, lng):
    with st.spinner('Loading data...'):
        res = api_calls(lat, lng)

    if res[0]: #success
        ph, temp, humidity = res[1]
        st.write('pH:', format_float(ph))
        st.write('Temperature:', format_float(temp))
        st.write('Humidity:', format_float(humidity))
    else:
        st.write(res[1])
        return

    '''try:
        crop_recommendations = crop_recommender_model(ph, temperature, humidity)
        st.write(crop_recommendations)
    except Exception as e:
        print(e)
        error = "Encountered error when training model or creating recommendation"
        st.write(error)'''




def api_calls(lat, lng):
    soil_headers = {'Content-type': "application/json"}
    soil_params = {
        "lat": lat,
        "lon": lng,
        'property': ['phh2o'],
        'depth': ['0-5cm'],
        'value': 'mean'
    }
    soil_parsed = parse_response(request(SOIL_URL, soil_headers, soil_params))

    try:
        ph = soil_parsed['properties']['layers'][0]['depths'][0]['values']['mean'] / 10
    except:
        return (False, "No pH data for this region!")
        
    ambee_headers = {
        'x-api-key': AMBEE_API_KEY,
        'Content-type': "application/json"
    }
    ambee_params = {"lat": lat, "lng": lng}
    ambee_parsed = parse_response(request(AMBEE_URL, ambee_headers, ambee_params))

    try:
        temp = (ambee_parsed['data']['temperature'] - 32) * 5 / 9
    except:
        return (False, "No temperature data for this region!")

    try:
        humidity = ambee_parsed['data']['humidity'] * 100
    except:
        return (False, "No humidity data for this region!")

    return (True, [ph, temp, humidity])
        

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


def handle_map():
    m = folium.Map()
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


def handle_address():
    address = st.text_input('Enter address')

    if address:
        suggestions_url = f"https://maps.googleapis.com/maps/api/place/autocomplete/" + \
            f"json?input={'%20'.join(address.split())}" + \
            f"&key={GOOGLE_MAPS_API_KEY}"

        options = [i['description'] for i in parse_response(request(suggestions_url))['predictions']]
        address = st.selectbox('suggestions', options)

        address_url = 'https://maps.googleapis.com/maps/api/geocode/json?address=' + \
            '%20'.join(address.split()) + \
            f"&key={GOOGLE_MAPS_API_KEY}"

        latlng = parse_response(request(address_url))['results'][0]['geometry']['location']
        try:
            lat, lng = latlng['lat'], latlng['lng']
        except IndexError:
            st.write('Latitude & longitude could not be found!')
            return

        m2 = folium.Map([lat, lng], zoom_start=ZOOM_LEVEL)
        folium.Marker([lat, lng]).add_to(m2)
        map2 = st_folium(m2, height=350, width=700)
        display_info(lat, lng)


def handle_latlng():
    col1, col2 = st.columns(2)
    with col1:
        lat = st.text_input('Enter latitude')
    with col2:
        lng = st.text_input('Enter longitude')

    if lat and lng:
        if not valid_lat_lng(lat, lng):
            st.write('invalid values - try again')
            return
            
        m3 = folium.Map([lat, lng], zoom_start=ZOOM_LEVEL)
        folium.Marker([lat, lng]).add_to(m3)
        map3 = st_folium(m3, height=350, width=700)
        display_info(lat, lng)


map_option, address_option, latlng_option = st.tabs(["Map", "Address", "Lat / Long"])
with map_option:
    handle_map()
with address_option:
    handle_address()
with latlng_option:
    handle_latlng()
