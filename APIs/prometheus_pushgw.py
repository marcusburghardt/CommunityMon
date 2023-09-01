#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Script created to help sending custom metrics to Prometheus through
the Pushgateway.

Author: Marcus Burghardt - https://github.com/marcusburghardt
"""

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from common import (
    CONF_FILE,
    create_dict_from_list,
    get_delta_time,
    get_github_metrics,
    get_parameter_value
    )


def create_pushgateway_registry():
    return CollectorRegistry()


def create_pushgateway_gauge_metric(unit, description, value, registry):
    metric = Gauge(unit, description, registry=registry)
    metric.set(value)
    return registry


def create_workflows_runs_metric(
        unit: str, description: str, registry: CollectorRegistry) -> Gauge:
    metric = Gauge(unit, description, ['status'], registry=registry)
    return metric


def append_workflows_runs_metric(metric: object, status: str, value: float) -> Gauge:
    metric.labels(status=status).set(value)
    return metric


def parse_repo_metrics(repo_metrics, registry):
    for metric in repo_metrics:
        registry = create_pushgateway_gauge_metric(
            metric['metric'],
            metric['description'],
            metric['value'],
            registry)
    return registry


def parse_workflow_metrics(workflow_info: dict) -> dict:
    workflow_metrics = {}
    workflow_status = get_github_metrics('workflows')['status']
    status_dict = create_dict_from_list(workflow_status)
    conclusion_str = workflow_info['conclusion']
    conclusion = status_dict[conclusion_str]
    duration = get_delta_time(workflow_info['created_at'], workflow_info['updated_at'], 's')
    workflow_metrics.update({'conclusion_status': conclusion})
    workflow_metrics.update({'duration_seconds': duration})
    return workflow_metrics


def append_pushgateway_metrics(
        metrics: dict, metric_id: str, value: str, description: str) -> dict:
    metrics.append({'metric': metric_id,
                    'value': value,
                    'description': description})
    return metrics


def push_pushgateway_metrics(registry):
    target = get_parameter_value(CONF_FILE, 'prometheus', 'push_target')
    job_name = get_parameter_value(CONF_FILE, 'prometheus', 'push_job')
    push_to_gateway(target, job=job_name, registry=registry)
