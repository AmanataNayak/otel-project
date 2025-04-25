from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import ConsoleLogExporter, SimpleLogRecordProcessor
from resource_utils import create_log_resource

#otel-collector
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

logger_provider = LoggerProvider(
    resource=create_log_resource()
)

# SDK Implementation
# logger_provider.add_log_record_processor(SimpleLogRecordProcessor(ConsoleLogExporter()))

# Collector Implementation
logger_provider.add_log_record_processor(SimpleLogRecordProcessor(exporter=OTLPLogExporter(insecure=True)))

handler = LoggingHandler(logger_provider=logger_provider)