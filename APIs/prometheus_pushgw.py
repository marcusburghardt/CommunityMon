#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Script created to help sending custom metrics to Prometheus through
the Pushgateway.

Author: Marcus Burghardt - https://github.com/marcusburghardt
"""

from common import *
from prometheus_client import CollectorRegistry, Counter, Gauge, push_to_gateway

def create_pushgateway_registry():
    return CollectorRegistry()

def create_pushgateway_gauge_metric(unit, description, value, registry):
    metric = Gauge(unit, description, registry=registry)
    metric.set(value)
    return registry

def parse_repo_metrics(repo_metrics, registry):
    for metric in repo_metrics:
        registry = create_pushgateway_gauge_metric(metric['metric'],
                                                   metric['description'],
                                                   metric['value'],
                                                   registry)
    return registry

def push_pushgateway_metrics(registry):
    target = get_parameter_value(CONF_FILE, 'prometheus', 'push_target')
    job_name = get_parameter_value(CONF_FILE, 'prometheus', 'push_job')
    push_to_gateway(target, job=job_name, registry=registry)
