import socket
from opentelemetry.sdk.resources import Resource, ResourceDetector
from opentelemetry.semconv.resource import ResourceAttributes


class HostDetector(ResourceDetector):
    def detect(self) -> Resource: 
        return Resource.create(
            {
                ResourceAttributes.HOST_NAME: socket.gethostname()
            }
        )
    

def create_resource(name: str, version: str) -> Resource:
    svc_resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: name,
            ResourceAttributes.SERVICE_VERSION: version
        }
    )

    host_rc = HostDetector().detect()
    rc = host_rc.merge(svc_resource)
    return rc

def create_log_resource() -> Resource:
    return Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: 'example_app'
        }
    )