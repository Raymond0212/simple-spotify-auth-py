from flask import Flask, redirect, request, session
import requests
import base64
import time
import argparse
import dbus
import dbus.service
import dbus.mainloop.glib
import json
from gi.repository import GLib

app = Flask(__name__)

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Spotify Auth App')
parser.add_argument('--client_id', required=True, help='Spotify Client ID')
parser.add_argument('--client_secret', required=True, help='Spotify Client Secret')
parser.add_argument('--port', type=int, default=2233, help='Port to run the app on')
args = parser.parse_args()

CLIENT_ID = args.client_id
CLIENT_SECRET = args.client_secret
REDIRECT_URI = f'http://localhost:{args.port}/callback'
PORT = args.port

# Spotify API endpoints
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

token = None

@app.route('/')
def index():
    return '<h1>Spotify API Auth For Gnome Top Bar</h1><a href="/login">Login with Spotify</a>'

@app.route('/login')
def login():
    scope = "user-read-private user-read-email app-remote-control streaming"
    auth_url = f"{SPOTIFY_AUTH_URL}?response_type=code&client_id={CLIENT_ID}&scope={scope}&redirect_uri={REDIRECT_URI}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')

    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth_str = base64.urlsafe_b64encode(auth_str.encode()).decode()
    headers = {
        "Authorization": f"Basic {b64_auth_str}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    response = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data=data)
    response_data = response.json()

    response_data['timestamp'] = time.time()
    global token 
    token = json.dumps(response_data)

    return '<h1>Authentication complete. You can close this window.</h1>'

class SpotifyTokenService(dbus.service.Object):
    def __init__(self, bus_name, object_path):
        super().__init__(bus_name, object_path)

    @dbus.service.method('com.gnome.SpotifyTokenService', in_signature='', out_signature='s')
    def GetToken(self):
        global token
        return token

def run_dbus_service():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus_name = dbus.service.BusName('com.gnome.SpotifyTokenService', bus=dbus.SessionBus())
    service = SpotifyTokenService(bus_name, '/com/gnome/SpotifyTokenService')
    mainloop = GLib.MainLoop()
    mainloop.run()

if __name__ == '__main__':
    from threading import Thread
    Thread(target=run_dbus_service).start()
    app.run(port=PORT)
