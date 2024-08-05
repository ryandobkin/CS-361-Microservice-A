
## Microservice A - CS 361
### api_interface.py
api_interface is an api interface program that takes dictionaries, parses the data, calls appropriate apis, then returns data via dictionary.
### Instructions
#### 1. How to call the microservice
**First**, configure your ZeroMQ socket to port 5559. This port is defined by a global variable SOCKET_PORT, so feel free to update it.
 **Second**, configure a request message to be sent. This message should be a dictionary in the following form:
```
{"service": "ai", 
 "data", {
	"role": "user",
	"model": "llama3-8b-8192",
	"content": "Example prompt"
}}
```
Note that the service value should remain as 'ai' to request from that service. The values for 'role', 'model', and 'content' are all up to the requestee at to their content.
**Third**, to send the request to the microservice, first convert the request from a dictionary to a json by doing: 
```
import zmq
import json

message = {"service": "ai", "data": {"role": "ex", "model": "ex", "content": "ex"}}
request_message = json.dumps(message)
```
**Finally**, to send the message, use:
```
socket.send(request_message.encode())
```
#### 2. How to receive a response from the microservice
**First**, after sending a message using the steps involved in *1. How to call the microservice*, create a blocking function awaiting a response through:
```
response_message = socket.recv()
```
This will stop your program loop and await a response from the microservice. When it is received, it will be assigned to response_data.
**Second**, to interpret the data, in either one line or as follows, process the message as so:
```
decoded_response_message = response_message.decode()
dict_response_message = json.loads(decoded_response_message)
```
At this point, dict_response_message will contain your response data. It will be formatted as follows:
```
{"service": "ai", "request": {*request_ex*}, "response": "ex", "time_taken": 0.19}
```
### UML Diagram:

![UML Diagram](http://github.com/ryandobkin/CS-361-Microservice-A/blob/main/Drawing3.png?raw=true)
