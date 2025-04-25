import time
import logging
import json
import requests
from fastapi import FastAPI, Request, Response, Depends
from fastapi.responses import JSONResponse
from opentelemetry.trace import get_current_span
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.propagate import inject, extract
from opentelemetry import context

from client import ChaosClient, FakerClient
from trace_utils import create_tracer
from metrics_utils import create_meter, create_request_instruments, create_resource_instruments
from logging_utils import handler

# Logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(process)d - %(levelname)s - %(message)s'
)

logger = logging.getLogger()
logger.addHandler(handler)

# Global variables
app = FastAPI()
tracer = create_tracer('app.py', '0.1')
meter = create_meter('app.py', '0.1')

# Instrumentation
request_instruments = create_request_instruments(meter)
create_resource_instruments(meter)
db = ChaosClient(client=FakerClient())


@app.middleware("http")
async def add_tracing_and_metrics(request: Request, call_next):
    # Trace
    ctx = extract(request.headers)
    previous_ctx = context.attach(ctx)
    request.state.previous_ctx_token = previous_ctx

    # Metric
    request_instruments['traffic_volume'].add(
        1,
        attributes={'http.route': request.url.path}
    )
    request.state.request_start = time.time_ns()

    try:
        response = await call_next(request)
    finally:
        context.detach(previous_ctx)

    # After request
    request_end = time.time_ns()
    duration = (request_end - request.state.request_start) / 1_000_000_000  # Convert ns to s

    request_instruments['error_rate'].add(1, {
        'http.route': request.url.path,
        'state': 'success' if response.status_code < 400 else 'fail'
    })

    request_instruments['request_latency'].record(
        duration,
        attributes={
            'http.request.method': request.method,
            'http.route': request.url.path,
            'http.response.status_code': response.status_code
        }
    )

    return response


@app.get("/users")
@tracer.start_as_current_span('users')
async def get_user():
    user, status = db.get_user(123)
    logging.info(f'Found user {user!s} with status {status}')
    data = {}
    if user is not None:
        data = {"id": user.id, "name": user.name, "address": user.address}
    else:
        logging.warning(f"Could not find user with id {123}")
        logging.debug(f"Collected data is {data}")
    logging.debug(f"Generated response {data}")
    return JSONResponse(content=data, status_code=status)


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


@app.get("/")
@tracer.start_as_current_span('index')
async def index():
    span = get_current_span()
    span.set_attributes(
        {
            SpanAttributes.HTTP_REQUEST_METHOD: "GET",
            SpanAttributes.URL_PATH: "/",
            SpanAttributes.HTTP_RESPONSE_STATUS_CODE: 200
        }
    )
    logging.info('Info from the index function')
    do_stuff()
    current_time = time.strftime("%a, %d %b %Y %H:%M:%S", time.gmtime())
    return {"message": f"Hello, World! It's currently {current_time}"}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='localhost')