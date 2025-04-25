import psutil

#Otel SDK
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
    MetricReader
)
from opentelemetry.metrics import Counter, Histogram, ObservableGauge
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.view import (
    View,
    DropAggregation,
    ExplicitBucketHistogramAggregation
)
#Metric API
from opentelemetry import metrics as metrics_api

# OTEL Collector
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

from resource_utils import create_resource
# View
def create_views() -> list[View]:
    views = []

    traffic_volume_change_name = View(
        instrument_type=Counter,
        instrument_name="traffic_volume",
        name="test",
    )

    views.append(traffic_volume_change_name) 

    # drop entire intrument
    drop_instrument = View(
        instrument_type=ObservableGauge,
        instrument_name="process.cpu.utilization",
        aggregation=DropAggregation(),
    )
    views.append(drop_instrument) 

    # change the aggregation (buckets) for all histogram instruments
    histrogram_explicit_buckets = View(
        instrument_type=Histogram,
        instrument_name="*",  #  supports wildcard pattern matching
        aggregation=ExplicitBucketHistogramAggregation((1, 21, 50, 100, 1000)),
    )
    views.append(histrogram_explicit_buckets) 

    return views 



def create_metrics_pipeline(export_interval: int) -> MetricReader:
    # SDK implementation
    # console_expoter = ConsoleMetricExporter()
    # reader = PeriodicExportingMetricReader(
    #     exporter=console_expoter,
    #     export_interval_millis=export_interval
    # )
    # return reader

    # Collector implementation
    exporter = OTLPMetricExporter(insecure=True)
    reader = PeriodicExportingMetricReader(
        exporter=exporter,
        export_interval_millis=export_interval
    )
    return reader


def create_meter(name: str, version: str) -> metrics_api.Meter:
    views = create_views()
    rc = create_resource(name, version)
    metrics_reader = create_metrics_pipeline(5000)
    provider = MeterProvider(
        metric_readers=[metrics_reader],
        resource=rc,
        views=views
    )

    # obtain meter
    metrics_api.set_meter_provider(provider)
    meter = metrics_api.get_meter(name, version)
    return meter



def create_request_instruments(meter: metrics_api.Meter) -> dict[str, metrics_api.Instrument]:
    ### Four golden signals
    ## 1. Traffic 
    traffic_volume = meter.create_counter(
        name='traffic_volume',
        unit='request',
        description='Total volume of requests to an endpoint'
    )

    ## 2. Error
    error_rate = meter.create_counter(
        name='error_rate',
        unit='request',
        description='Rate of failed requests'
    )

    ## 3. Latency
    request_latency = meter.create_histogram(
        name='http.server.request.duration',
        unit='s',
        description='latency for a request to be served',
    )

    instruments = {
        'traffic_volume': traffic_volume,
        'error_rate': error_rate,
        'request_latency': request_latency
    }

    return instruments

def create_resource_instruments(meter: metrics_api.Meter) -> dict[str, metrics_api.Instrument]:
    cpu_util_gauge = meter.create_observable_gauge(
        name="process.cpu.utilization",
        callbacks=[
            lambda x: [metrics_api.Observation(psutil.cpu_percent(interval=1) / 100)]
        ],
        unit="1",
        description="CPU utilization",
    )

    memory_usage_gauge = meter.create_observable_up_down_counter(
        name="process.memory.usage",
        callbacks=[lambda x: [metrics_api.Observation(psutil.virtual_memory().used)]],
        unit="By",
        description="total amount of memory used",
    )

    instruments = {"cpu_utilization": cpu_util_gauge, "memory_used": memory_usage_gauge}
    return instruments