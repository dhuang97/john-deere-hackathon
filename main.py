"""Provides optimal crop suggestions based on location using weather and soil data"""

import os
import time
from datetime import date, timedelta
import json

from dotenv import load_dotenv
import numpy as np
import streamlit as st
from streamlit_folium import st_folium
import requests
import folium
from folium.plugins import MousePosition


load_dotenv('credentials.env')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
AMBEE_API_KEY = os.getenv('AMBEE_API_KEY')


SOIL_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
ZOOM_LEVEL = 15


@st.cache
def read_data():
    """Read in reference data for optimal soil & weather conditions for crops"""

    csv = np.genfromtxt('Crop_recommendation.csv', delimiter=',', \
        dtype=None, encoding=None)[1:, [3,4,5,7]]

    crops = csv[:, -1]
    data = csv[:, :-1].astype('float32')

    return data, crops

data_table, crops_table = read_data()


st.title("Crop Optimization By Location")
st.write("Based on soil properties and weather conditions")


def format_float(num):
    """Round float to 2 decimals"""
    return round(num, 2)


def request(url, headers=None, params=None):
    """Request website data"""
    return requests.get(url, headers=headers, params=params, timeout=15)


def parse_response(resp):
    """Convert website response to json"""
    return json.loads(resp.text)


def valid_lat_lng(lat, lng):
    """Check validity of lat & lng"""

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
    """Show data and results after location data is obtained"""

    with st.spinner('Loading environment data...'):
        res = api_calls(lat, lng)

    if res[0]: #success
        ph, temp, humidity = res[1]

        st.header('Average soil info:')
        st.write('pH:', format_float(ph))
        st.write('Temperature (°C):', format_float(temp))
        st.write('Relative humidity:', format_float(humidity))
    else:
        st.write(res[1])
        return

    with st.spinner('Computing suggested crops...'):
        time.sleep(1)
        vals = [temp, humidity, ph]
        mse = (np.square(vals - data_table)).mean(axis=1)

        suggestions = []

        idx = mse.argsort()
        i = 0
        while len(suggestions) < 3:
            crop = crops_table[idx[i]]
            if not crop in suggestions:
                suggestions.append(crop)
            i += 1

        st.header('Suggested crops:')
        for ind, i in enumerate(suggestions):
            st.write(ind+1, i)


def api_calls(lat, lng):
    """Make calls to get soil & weather data from APIs"""

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
    except TypeError:
        return (False, "No pH data for this region!")

    today = date.today()
    yesterday = today - timedelta(days = 1)


    url = f'https://api.ambeedata.com/weather/history/daily/by-lat-lng?lat={lat}&lng={lng}&' + \
        f'from={yesterday}%2000:00:00&to={today}%2000:00:00' + \
        '&x-api-key=574ff7cf7f9cff3669b45812fc5d6f2372f1b73c4a40b89fb0d0ae9ea34175ab&units=si'
    ambee_parsed = parse_response(request(url))

    try:
        temp = ambee_parsed["data"]["history"][0]["temperature"]
    except TypeError:
        return (False, "No temperature data for this region!")

    try:
        humidity = ambee_parsed["data"]["history"][0]["humidity"] * 100
    except TypeError:
        return (False, "No humidity data for this region!")

    return (True, [ph, temp, humidity])


def handle_map():
    """Run when on map tab"""

    map1 = folium.Map()
    formatter = "function(num) {return L.Util.formatNum(num, 3) + ' º ';};"

    MousePosition(position="topright",
                    separator=" | ",
                    empty_string="NaN",
                    prefix="Coordinates:",
                    lat_formatter=formatter,
                    lng_formatter=formatter).add_to(map1)

    map1.add_child(folium.LatLngPopup())
    map_data = st_folium(map1, height=350, width=700)

    if map_data['last_clicked']:
        lat, lng = map_data['last_clicked']['lat'], map_data['last_clicked']['lng']
        display_info(lat, lng)


def handle_address():
    """Run when on address tab"""

    address = st.text_input('Enter address')

    if address:
        suggestions_url = "https://maps.googleapis.com/maps/api/place/autocomplete/" + \
            f"json?input={'%20'.join(address.split())}" + \
            f"&key={GOOGLE_MAPS_API_KEY}"

        options = [i['description'] for i in \
            parse_response(request(suggestions_url))['predictions']]

        if len(options) > 0:
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

            map2 = folium.Map([lat, lng], zoom_start=ZOOM_LEVEL)
            folium.Marker([lat, lng]).add_to(map2)
            st_folium(map2, height=350, width=700)
            display_info(lat, lng)

        else:
            st.write('Invalid address, please try again!')


def handle_latlng():
    """Run when on lat/lng tab"""

    col1, col2 = st.columns(2)
    with col1:
        lat = st.text_input('Enter latitude')
    with col2:
        lng = st.text_input('Enter longitude')

    if lat and lng:
        if not valid_lat_lng(lat, lng):
            st.write('invalid values - try again')
            return

        map3 = folium.Map([lat, lng], zoom_start=ZOOM_LEVEL)
        folium.Marker([lat, lng]).add_to(map3)
        st_folium(map3, height=350, width=700)
        display_info(lat, lng)


map_option, address_option, latlng_option = st.tabs(["Map", "Address", "Lat / Long"])
with map_option:
    handle_map()
with address_option:
    handle_address()
with latlng_option:
    handle_latlng()
