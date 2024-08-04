import time
import json
import requests
import zmq
import GLOBALS
import os
from groq import Groq


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

            api_interface = APIInterface(json.loads(message.decode()), socket)
            api_interface.run()

            # print("Created Interface Thread")

            # Send reply back to client

    except KeyboardInterrupt:
        print("Program Stopped")
        exit(0)


class APIInterface:
    """
    Holds methods to parse requests, send requests to api, parse responses, then send them back to user.
    """
    def __init__(self, request, ret_socket):
        self.request = request
        # self.parsed_request = None
        self.start_time = time.time()

    def run(self):
        self.parse_request()

    def parse_request(self):
        """
        Parses the incoming request message. Determines what API should be called.

        Incoming request messages should be structured as a dictionary as follows:

        location_query : str - e.g. "San Diego, CA, USA" - full places autocomplete response string
        {"service": "google_places_geocode",
        "data": location_query}
        OR
        search_query : str - e.g. "San Di"
        {"service": "google_places_autocomplete",
        "data": search_query}
        OR
        search_query_coordinates : list - e.g. [lat, lng] - [36.6041944, -117.8738554] - typically 7 decimals
        {"service": "nws",
        "data": search_query_coordinates}
        OR
        ai_request : dict - e.g. {"roll": "user", "model": "llama3-8b-8192", "content": "Compose a poem..."}
        {"service": "ai",
        "data": ai_request}
        OR
        {"service": "update_google_api_key",
        "data": api_key}
        OR
        {"service": "update_openai_api_key",
        "data": api_key}
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
        elif service == "update_google_api_key":
            pass
        elif service == "update_anthropic_api_key":
            pass
        else:
            self.error("service")

    def google_places_geocode(self, data, retry_counter=0):
        """
        Calls the Google Places (new) geocoding API with incoming request data.
        Working
        """
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
                self.error("api")
            self.google_places_geocode(data, retry_counter)
        response_data = {
            "service": "geocoding",
            "request": self.request,
            "response": (response["results"][0]["geometry"]["location"]["lat"],
                         response["results"][0]["geometry"]["location"]["lng"]),
            "time_taken": (time.time() - self.start_time)}
        self.return_response(response_data)

    def google_places_autocomplete(self, data, retry_counter=0):
        """
        Calls the Google Places (new) autocomplete API with incoming query data.
        Working
        """
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

    def nws(self, data):
        """
        Calls the NWS API with incoming coordinate data.
        Working
        """
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

    def ai(self, data=None):
        """
        Calls an AI API [groq] to generate a request with AI.
        """
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

    def return_response(self, payload):
        """
        Returns a response to the request port.
        """
        socket.send(json.dumps(payload).encode())

    def error(self, error_point):
        """
        Catches invalid requests and returns useful error messages to user.
        """
        if error_point == "service":
            print("SERVICE ERROR")
        elif error_point == "api":
            print("API ERROR")





if __name__ == '__main__':
    main()
    pass
