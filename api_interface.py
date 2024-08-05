import time
import json
import requests
import zmq
import GLOBALS
import os
from groq import Groq

# Written by: Ryan Dobkin
# CS 361 Microservice A

SOCKET_PORT = '5559'
GOOGLE_API_KEY = GLOBALS.GOOGLE_API_KEY
AI_API_KEY = GLOBALS.AI_API_KEY


context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind(f"tcp://*:{SOCKET_PORT}")
print_resp = True


def main():
    try:
        while True:
            #  AWAIT CLIENT CONNECTION
            message = socket.recv()
            print(f"Received request: {message.decode()}")

            api_interface = APIInterface(json.loads(message.decode()))
            api_interface.run()

    except:
        print("Program Stopped")
        exit(0)


class APIInterface:
    """
    Holds methods to parse requests, send requests to api, parse responses, then send them back to user.
    """
    def __init__(self, request):
        self.request = request
        self.start_time = time.time()

    def run(self):
        self.parse_request()

    def parse_request(self):
        """
        Parses the incoming request message. Determines what API should be called.

        Incoming request messages should be structured as a dictionary as follows:

        location_query : str - e.g. "San Diego, CA, USA" - full places autocomplete response string
        {"service": "geocoding",
        "data": location_query}
        OR
        search_query : str - e.g. "San Di"
        {"service": "autocomplete",
        "data": search_query}
        OR
        search_query_coordinates : list - e.g. [lat, lng] - [36.6041944, -117.8738554] - typically 7 decimals
        {"service": "nws",
        "data": search_query_coordinates}
        OR
        ai_request : dict - e.g. {"role": "user", "model": "llama3-8b-8192", "content": "Compose a poem..."}
        {"service": "ai",
        "data": ai_request}
        """
        service = self.request["service"]
        if service == "geocoding":
            self.google_places_geocode(self.request["data"])
        elif service == "autocomplete":
            self.google_places_autocomplete(self.request["data"])
        elif service == "nws":
            self.nws(self.request["data"])
        elif service == "ai":
            self.ai(self.request["data"])
        else:
            self.error("parser")

    def google_places_geocode(self, data, retry_counter=0):
        """
        Calls the Google Places (new) geocoding API with incoming request data.
        Working
        """
        try:
            base_url = "https://maps.googleapis.com/maps/api/geocode/json?address="
            api_key = GOOGLE_API_KEY
            url_query = data.replace(" ", "+")
            request_url = base_url + url_query + "&key=" + api_key
            if print_resp:
                print(f"[API Interface] Calling geocoding API | data: {data} | url: {request_url}")
            response = requests.get(request_url)
            response = response.json()
            if response["status"] != "OK":
                print("[API Interface] GEOCODING REQUEST FAIL - RETRYING")
                retry_counter += 1
                if retry_counter == 4:
                    self.error("geocoding timeout")
                self.google_places_geocode(data, retry_counter)
            response_data = {
                "service": "geocoding",
                "request": self.request,
                "response": (response["results"][0]["geometry"]["location"]["lat"],
                             response["results"][0]["geometry"]["location"]["lng"]),
                "time_taken": (time.time() - self.start_time)}
            self.return_response(response_data)
        except:
            self.error("geocoding")

    def google_places_autocomplete(self, data):
        """
        Calls the Google Places (new) autocomplete API with incoming query data.
        Working
        """
        try:
            base_url = "https://places.googleapis.com/v1/places:autocomplete"
            api_key = GOOGLE_API_KEY
            params = {"input": data, "includedPrimaryTypes": "(cities)"}
            payload = json.dumps(params)
            headers = {'Content-Type': 'application/json', 'X-Goog-Api-Key': api_key}
            if print_resp:
                print(f"[API Interface] Calling autocomplete API | data: {data} |\n"
                      f"headers: {headers} | payload: {params} |\n"
                      f"url: {base_url}")
            response = requests.post(base_url, data=payload, headers=headers).json()
            query_prediction_list = []
            if "suggestions" in response:
                for _ in response["suggestions"]:
                    query_prediction_list.append(_['placePrediction']['text']['text'])
                self.return_response({
                    "service": "autocomplete",
                    "request": self.request,
                    "response": query_prediction_list,
                    "time_taken": (time.time() - self.start_time)})

            else:
                self.return_response({
                    "service": "autocomplete",
                    "request": self.request,
                    "response": [False],
                    "time_taken": (time.time() - self.start_time)})
        except:
            self.error("autocomplete")

    def nws(self, data):
        """
        Calls the NWS API with incoming coordinate data.
        Working
        """
        try:
            base_url = "https://api.weather.gov/points/"
            url_query = base_url + str(data[0]) + "," + str(data[1])
            if print_resp:
                print(f"[API Interface] NWS API Request - coordinates: {data} |\nurl: {url_query}")
            response = requests.get(url_query)
            response = response.json()
            # print("API REQUEST_WEATHER_JSON_GENERAL", response["properties"])
            self.return_response({
                "service": "nws",
                "request": self.request,
                "response": response,
                "time_taken": (time.time() - self.start_time)})
        except:
            self.error("nws")

    def ai(self, data=None):
        """
        Calls an AI API [groq] to generate a request with AI.
        """
        try:
            client = Groq(
                api_key=AI_API_KEY
            )

            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": data["role"],
                        "content": data["content"]
                    }
                ],
                model=data["model"]
            )
            response = chat_completion.choices[0].message.content
            self.return_response({
                "service": "ai",
                "request": self.request,
                "response": response,
                "time_taken": (time.time() - self.start_time)
            })
        except:
            self.error("ai")

    def return_response(self, payload):
        """
        Returns a response to the request port.
        """
        socket.send(json.dumps(payload).encode())

    def error(self, error_point):
        """
        Catches invalid requests and returns useful error messages to user.
        """
        self.return_response({"service": self.request["service"],
                              "request": self.request,
                              "response": f"ERROR: {error_point} service received an invalid request."})


if __name__ == '__main__':
    main()
