import time
# add the logging library
import logging
from opentelemetry.trace import get_current_span
from opentelemetry.semconv.trace import SpanAttributes
# this is required for networking traces
from opentelemetry.propagate import inject
import logging

import requests
import json
from client import ChaosClient, FakerClient
from flask import Flask, make_response, request, Response
#otel custom
from trace_utils import create_tracer
from metrics_utils import (create_meter, create_request_instruments, create_resource_instruments)


## Add traces for as a outgoing service
from opentelemetry.propagate import extract
from opentelemetry import context

# import logging handler
from logging_utils import handler

#Logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(process)d - %(levelname)s - %(message)s'
)

logger = logging.getLogger()
logger.addHandler(handler)

# global variables
app = Flask(__name__)
tracer = create_tracer('app.py', '0.1')
meter = create_meter('app.py', '0.1')

@app.route("/users", methods=["GET"])
@tracer.start_as_current_span('users')
def get_user():
    user, status = db.get_user(123)
    logging.info(f'Found user {user!s} with status {status}')
    data = {}
    if user is not None:
        data = {"id": user.id, "name": user.name, "address": user.address}
    else:
        logging.warning(f"Could not find user with id {123}")
        logging.debug(f"Collected data is {data}")
    response = make_response(data, status)
    logging.debug(f"Generated response {response}")
    return response


## Add traces for as a outgoing service
@app.teardown_request
def teardown_request_func(err):
    previous_ctx = request.environ.get("previous_ctx_token", None)
    if previous_ctx:
        context.detach(previous_ctx)

@app.before_request
def before_request_func():
    # trace
    ctx = extract(request.headers)
    previous_ctx = context.attach(ctx)
    request.environ["previous_ctx_token"] = previous_ctx

    # metirc
    request_instruments['traffic_volume'].add(
        1,
        attributes={'http.route': request.path}
    )

    request.environ['request_start'] = time.time_ns()

@app.after_request
def after_request_func(response: Response) -> Response:
    request_end = time.time_ns()
    request_instruments['error_rate'].add(1, {
        'http.route': request.path,
        'state': 'success' if response.status_code < 400 else 'fail'
    })
    duration = (request_end - request.environ['request_start']) / 1000000000 # convert ns to s

    request_instruments['request_latency'].record(
        duration,
        attributes = {
            'http.request.method': request.method,
            'http.route': request.path,
            'http.response.status_code': response.status_code
        }
    )

    return response

@tracer.start_as_current_span('do_stuff')
def do_stuff():
    headers = {}
    inject(headers)
    time.sleep(0.1)
    url = "http://localhost:6000/"
    response = requests.get(url, headers=headers)
    print("Headers included in outbound request:")
    print(json.dumps(response.json()["request"]["headers"], indent=2))
    return response


@app.route("/")
@tracer.start_as_current_span('index')
def index():
    span = get_current_span()
    span.set_attributes(
        {
            SpanAttributes.HTTP_REQUEST_METHOD : request.method,
            SpanAttributes.URL_PATH: request.path,
            SpanAttributes.HTTP_RESPONSE_STATUS_CODE: 200
        }
    )
    logging.info('Info from the index function')
    do_stuff()
    current_time = time.strftime("%a, %d %b %Y %H:%M:%S", time.gmtime())
    return f"Hello, World! It's currently {current_time}"


if __name__ == "__main__":
    # disable logs of builtin webserver for load test
    logging.getLogger("werkzeug").disabled = True

    # instrumentation
    request_instruments = create_request_instruments(meter)
    create_resource_instruments(meter)
    # launch app
    db = ChaosClient(client=FakerClient())
    app.run(host="0.0.0.0", debug=True, port=1234)
