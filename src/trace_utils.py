# Otel SDK
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
from opentelemetry.sdk.trace import TracerProvider

# Otel API
from opentelemetry import trace as trace_api

# Collector
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from resource_utils import create_resource


def create_tracing_pipeline() -> BatchSpanProcessor:
    # SDK Implementation
    # console_exporter = ConsoleSpanExporter()
    # span_processor = BatchSpanProcessor(console_exporter)
    # return span_processor
    
    # Collector Implementation
    exporter = OTLPSpanExporter()
    span_processor = BatchSpanProcessor(exporter)
    return span_processor

def create_tracer(name: str, version: str) -> trace_api.Tracer:
    provider = TracerProvider(
        resource=create_resource(name, version)
    )
    provider.add_span_processor(create_tracing_pipeline())
    trace_api.set_tracer_provider(provider)
    tracer = trace_api.get_tracer(name, version)
    return tracer

