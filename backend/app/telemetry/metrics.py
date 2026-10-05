import os

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation, View
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

if os.getenv("TELEMETRY_ENABLED", "false") in ("true", "yes", "1"):
    reader = PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=5000)
    resource = Resource.create({SERVICE_NAME: "arena-cat"})
    latency_view = View(
        instrument_name="http.server.duration",
        aggregation=ExplicitBucketHistogramAggregation(
            boundaries=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10)
        ),
    )

    provider = MeterProvider(metric_readers=[reader], views=[latency_view], resource=resource)
else:
    # No-op provider if not enabled.
    provider = MeterProvider()

metrics.set_meter_provider(provider)

meter = metrics.get_meter("arena-cat")

http_requests_total = meter.create_counter("http.server.requests", unit="{request}")

http_errors_total = meter.create_counter(
    "http.server.errors", unit="{error}", description="HTTP 5xx errors."
)

http_requests_duration = meter.create_histogram(
    "http.server.duration", unit="s", description="HTTP request latency."
)

tasks_served_total = meter.create_counter(
    "arena_cat.tasks.served", unit="{task}", description="Tasks served."
)

votes_total = meter.create_counter(
    "arena_cat.votes.total", unit="{vote}", description="Total votes saved after commiting."
)

task_skips_total = meter.create_counter(
    "arena_cat.task_skips.total", unit="{skip}", description="Total task skips."
)

registrations_total = meter.create_counter(
    "arena_cat.registrations.total", unit="{user}", description="Total users registered."
)

qualifications_total = meter.create_counter(
    "arena_cat.qualifications.total",
    unit="{user}",
    description="Qualified users (only registered the first time a user passes the qualification)",
)

email_errors_total = meter.create_counter(
    "arena_cat.email_errors.total", unit="{error}", description="Total errors when sending emails."
)
