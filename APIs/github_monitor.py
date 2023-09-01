#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Script created to easily interact with the Github API and return results
in formats consumable by humans or monitoring tools.

Author: Marcus Burghardt - https://github.com/marcusburghardt
"""

# First version: 2022-04-12
#
# References:
# - https://developer.github.com/v3/libraries/
# - https://github.com/PyGithub/PyGithub
# - https://pygithub.readthedocs.io/en/latest/github_objects.html
# - https://docs.github.com/en/rest

from argparse import ArgumentParser
from github import Github
from github.Milestone import Milestone
from github.NamedUser import NamedUser
from github.Organization import Organization
from github.Repository import Repository
from prometheus_client import CollectorRegistry

from common import (
    create_canonical_name,
    create_dict_from_string,
    create_list_from_string,
    parse_filters_string,
    get_delta_time,
    get_github_labels,
    get_github_metrics,
    get_github_token,
    get_old_date,
    print_object_info,
    print_object_info_header,
    )
from prometheus_pushgw import (
    append_pushgateway_metrics,
    create_pushgateway_gauge_metric,
    create_pushgateway_registry,
    parse_repo_metrics,
    push_pushgateway_metrics,
    )


def create_github_session() -> Github:
    return Github(get_github_token())


def count_items_by_owner(items: list, owners: list) -> int:
    count = 0
    for item in items:
        if item.user.login in owners:
            count += 1
    return count


def count_repository_open_items_unassigned(items: list) -> int:
    count = 0
    for item in items:
        if item.assignee is None:
            count += 1
    return count


def filter_created_items_by_lifetime(items: list, days: int) -> list:
    recent_items = []
    for item in items:
        if item.created_at < get_old_date(days):
            break
        recent_items.append(item)
    return recent_items


def filter_outdated_items(items: list, days: int) -> list:
    old_open_items = []
    for item in items:
        if item.updated_at < get_old_date(days):
            old_open_items.append(item)
    return old_open_items


def filter_pulls_from_issues(items: list) -> list:
    pulls_list = []
    for item in items:
        if item.pull_request:
            pulls_list.append(item)
    return pulls_list


def filter_repository_open_items_team(items: list) -> list:
    open_items_team = []
    team_members = get_github_metrics('team')
    for item in items:
        if item.user.login in team_members:
            open_items_team.append(item)
    return open_items_team


def get_organization_object(session: Github, org_id: str) -> Organization:
    return session.get_organization(org_id)


def get_repository_object(session: Github, repo_id: str) -> Repository:
    return session.get_repo(repo_id)


def get_milestone_by_title(repo, milestone_title: str) -> Milestone:
    if milestone_title in ['none', '*']:
        return milestone_title
    milestones = repo.get_milestones()
    for item in milestones:
        if item.title == milestone_title:
            return item
    raise Exception("The milestone title was not found!")


def get_user_by_login(session: Github, user_login: str) -> NamedUser:
    if user_login in ['none', '*']:
        return user_login
    return session.get_user(login=user_login)


def get_members_list(session: Github, org_id: str, role: str) -> list:
    org = get_organization_object(session, org_id)
    return org.get_members(role=role)


def get_repositories_list(session: Github, org_id: str) -> list:
    org = get_organization_object(session, org_id)
    return org.get_repos(type='all')


def get_repository_contributors(session: Github, repo_id: str) -> list:
    repo = get_repository_object(session, repo_id)
    return repo.get_contributors()


def get_repository_created_issues(
        session: Github, repo_id: str, days: str, filter_string: str) -> list:
    open_issues = get_repository_issues(session, repo_id, filter_string, '')
    return filter_created_items_by_lifetime(open_issues, days)


def get_repository_created_pulls(
        session: Github, repo_id: str, days: int, filter_string: str) -> list:
    open_pulls = get_repository_pulls(session, repo_id, filter_string)
    return filter_created_items_by_lifetime(open_pulls, days)


def get_repository_events(session: Github, repo_id: str) -> list:
    repo = get_repository_object(session, repo_id)
    return repo.get_events()


def get_repository_infos(session: Github, repo_id: str) -> dict:
    repo = get_repository_object(session, repo_id)
    labels_count = get_repository_labels(session, repo_id)
    infos = {'forks_count': repo.forks_count, 'stargazers_count': repo.stargazers_count,
             'subscribers_count': repo.subscribers_count, 'archived': repo.archived,
             'private': repo.private, 'open_issues_count': repo.open_issues_count,
             'labels_count': labels_count.totalCount}
    return infos


def get_repository_issues(
        session: Github, repo_id: str, filters_string: str, labels_string: str) -> list:
    filters_dict = create_dict_from_string(filters_string, ',')
    filters = parse_filters_string(filters_dict, 'issue')
    assignee = get_user_by_login(session, filters['assignee'])
    repo = get_repository_object(session, repo_id)
    milestone = get_milestone_by_title(repo, filters['milestone'])

    if labels_string:
        labels_list = create_list_from_string(labels_string, ',')
        filtered_issues = repo.get_issues(state=filters['state'],
                                          labels=labels_list)
    else:
        filtered_issues = repo.get_issues(state=filters['state'],
                                          assignee=assignee,
                                          milestone=milestone)
    return filtered_issues


def get_repository_label_usage_count(session: Github, repo_id: str, label: str) -> None:
    open_filter_string = 'state=open'
    open_issues = get_repository_issues(session, repo_id, open_filter_string, label)
    closed_filter_string = 'state=closed'
    closed_issues = get_repository_issues(session, repo_id, closed_filter_string, label)
    print(f'{label},{open_issues.totalCount},{closed_issues.totalCount}')


def get_repository_labels(session: Github, repo_id: str) -> list:
    repo = get_repository_object(session, repo_id)
    return repo.get_labels()


def get_repository_outdated_issues(session: Github, repo_id: str, days: int) -> list:
    filter_string = "state=open"
    open_issues = get_repository_issues(session, repo_id, filter_string, '')
    return filter_outdated_items(open_issues, days)


def get_repository_outdated_pulls(session: Github, repo_id: str, days: int) -> list:
    filter_string = "state=open"
    open_pulls = get_repository_pulls(session, repo_id, filter_string)
    return filter_outdated_items(open_pulls, days)


def get_repository_pulls(session: Github, repo_id: str, filters_string: str) -> list:
    repo = get_repository_object(session, repo_id)
    if filters_string:
        filters_dict = create_dict_from_string(filters_string, ',')
        filters = parse_filters_string(filters_dict, 'pull')
        filtered_pulls = repo.get_pulls(state=filters['state'], sort=filters['sort'],
                                        direction=filters['direction'])
        return filtered_pulls
    else:
        return repo.get_pulls()


def get_items_lifetime_average(items: list, days: int, lifetime_info: dict,
                               state='closed') -> dict:
    # INFO: Getting detailed info from all items can hit the API limits and take long time
    # depending on the project activity. Therefore, this function limits the items by ignoring
    # items older than N "days". The API returns items ordered by closed or created datetime
    # depending on the items state in the list, so the loop can be safely stopped as soon as the
    # first old item is found. This API behavior might change along the time.
    lifetime_in_minutes = 0
    lifetime_in_minutes_team = 0
    lifetime = 0
    lifetime_team = 0
    processed_items = 0
    processed_items_team = 0
    team_members = get_github_metrics('team')

    for item in items:
        if state == 'closed':
            if item.closed_at < get_old_date(days):
                break
            delta_time = get_delta_time(item.created_at, item.closed_at, 'm')
        else:
            delta_time = get_delta_time(item.created_at, item.updated_at, 'm')
        lifetime_in_minutes += delta_time
        processed_items += 1

        if item.user.login in team_members:
            lifetime_in_minutes_team += delta_time
            processed_items_team += 1

    if processed_items:
        lifetime = lifetime_in_minutes//processed_items

    if processed_items_team:
        lifetime_team = lifetime_in_minutes_team//processed_items_team

    lifetime_info.update({f'{state}_count': processed_items})
    lifetime_info.update({f'{state}_lifetime': lifetime})
    lifetime_info.update({f'{state}_count_team': processed_items_team})
    lifetime_info.update({f'{state}_lifetime_team': lifetime_team})
    return lifetime_info


def collect_created_items(
        repo_id: str, metrics: dict, created_items: list, timeframe: str, type: str) -> dict:
    repo_name = create_canonical_name(repo_id)
    metric = f'{repo_name}_created_{type}_{timeframe}days'
    description = f'Number of created {type} within last {timeframe} days on {repo_id}'
    metrics = append_pushgateway_metrics(metrics, metric, len(created_items), description)
    # By team
    count = collect_created_issues_by_team(created_items)
    metric = f'{repo_name}_created_{type}_by_team_{timeframe}days'
    description = f'Number of {type} created by team within last {timeframe} days on {repo_id}'
    metrics = append_pushgateway_metrics(metrics, metric, count, description)
    return metrics


def collect_created_issues_by_team(issues: list) -> int:
    team_members = get_github_metrics('team')
    return count_items_by_owner(issues, team_members)


def collect_created_issues(session: Github, repo_id: str, metrics: dict) -> dict:
    filter_string = "state=all"
    for timeframe in get_github_metrics('timeframe'):
        created_issues = get_repository_created_issues(session, repo_id, timeframe, filter_string)
        metrics = collect_created_items(repo_id, metrics, created_issues, timeframe, 'issues')
    return metrics


def collect_created_pulls_by_team(pulls: list) -> int:
    team_members = get_github_metrics('team')
    return count_items_by_owner(pulls, team_members)


def collect_created_pulls(session: Github, repo_id: str, metrics: dict) -> dict:
    filter_string = "state=all"
    for timeframe in get_github_metrics('timeframe'):
        created_pulls = get_repository_created_pulls(session, repo_id, timeframe, filter_string)
        metrics = collect_created_items(repo_id, metrics, created_pulls, timeframe, 'pulls')
    return metrics


def collect_org_metrics_prometheus(
        session: Github, org_id: str, registry) -> tuple[CollectorRegistry, list]:
    for metric in get_github_metrics('org'):
        if metric == 'members':
            org_members = get_members_list(session, org_id, 'all')
            count = org_members.totalCount
        elif metric == 'admins':
            org_admins = get_members_list(session, org_id, 'admin')
            count = org_admins.totalCount
        elif metric == 'repositories':
            org_repositories = get_repositories_list(session, org_id)
            count = org_repositories.totalCount
        elif metric == 'team_size':
            count = len(get_github_metrics('team'))
        else:
            print(f'Metric {metric} is not available.')
            continue
        registry = create_pushgateway_gauge_metric(f'{org_id}_org_{metric}',
                                                   f'Count of {metric} on {org_id} org',
                                                   count, registry)
    return registry, org_repositories


def collect_item_lifetime_average(
        repo_id: str, metrics: dict, lifetime_info: dict, timeframe: str,
        type: str, state='closed') -> dict:
    repo_name = create_canonical_name(repo_id)
    if state == 'closed':
        suffix = f'from last {timeframe} days'
        metric_suffix = f'_{timeframe}days'

        # count
        metric = f'{repo_name}_{state}_{type}{metric_suffix}'
        description = f'Number of {state} {type} on {repo_id} {suffix}'
        metrics = append_pushgateway_metrics(metrics, metric,
                                             lifetime_info[f'{state}_count'], description)
        # count team
        metric = f'{repo_name}_{state}_{type}{metric_suffix}_team'
        description = f'Number of {state} team {type} on {repo_id} {suffix}'
        metrics = append_pushgateway_metrics(metrics, metric,
                                             lifetime_info[f'{state}_count_team'], description)
    else:
        suffix = ''
        metric_suffix = ''

    # lifetime
    metric = f'{repo_name}_{state}_{type}_lifetime_average{metric_suffix}'
    description = f'Average lifetime of {state} {type} on {repo_id} {suffix}'
    metrics = append_pushgateway_metrics(metrics, metric,
                                         lifetime_info[f'{state}_lifetime'], description)
    # lifetime team
    metric = f'{repo_name}_{state}_{type}_lifetime_average{metric_suffix}_team'
    description = f'Average lifetime of {state} team {type} on {repo_id} {suffix}'
    metrics = append_pushgateway_metrics(metrics, metric,
                                         lifetime_info[f'{state}_lifetime_team'], description)
    return metrics


def collect_items_lifetime_average(
        repo_id: str, metrics: dict, closed_items: list, open_items: list, type: str) -> dict:
    lifetime_info = dict()
    for timeframe in get_github_metrics('timeframe'):
        lifetime_info = get_items_lifetime_average(closed_items, timeframe,
                                                   lifetime_info, 'closed')
        metrics = collect_item_lifetime_average(repo_id, metrics, lifetime_info, timeframe,
                                                type, 'closed')
    lifetime_info = get_items_lifetime_average(open_items, 0, lifetime_info, 'open')
    metrics = collect_item_lifetime_average(repo_id, metrics, lifetime_info, timeframe,
                                            type, 'open')
    return metrics


def collect_issues_lifetime_average(session: Github, repo_id: str, metrics: dict) -> dict:
    closed_filter = 'state=closed,sort=closed,direction=desc'
    open_filter = 'state=open,sort=opened,direction=desc'
    closed_issues = get_repository_issues(session, repo_id, closed_filter, '')
    open_issues = get_repository_issues(session, repo_id, open_filter, '')
    metrics = collect_items_lifetime_average(repo_id, metrics,
                                             closed_issues, open_issues, 'issues')
    return metrics


def collect_pulls_lifetime_average(session: Github, repo_id: str, metrics: dict) -> dict:
    closed_filter = 'state=closed,sort=closed,direction=desc'
    open_filter = 'state=open,sort=opened,direction=desc'
    closed_pulls = get_repository_pulls(session, repo_id, closed_filter)
    open_pulls = get_repository_pulls(session, repo_id, open_filter)
    metrics = collect_items_lifetime_average(repo_id, metrics,
                                             closed_pulls, open_pulls, 'pulls')
    return metrics


def collect_repository_info(session: Github, repo_id: str, metrics: dict) -> dict:
    repo_name = create_canonical_name(repo_id)
    repo_infos = get_repository_infos(session, repo_id)
    for repo_info in repo_infos.keys():
        description = f'Count of {repo_info} on {repo_id}'
        metrics = append_pushgateway_metrics(metrics, f'{repo_name}_{repo_info}',
                                             repo_infos[repo_info], description)
    return metrics


def collect_repository_items_by_label(
        repo_id: str, metrics: dict, items: list, label: str, state: str, item_type: str) -> dict:
    repo_name = create_canonical_name(repo_id)
    canonical_label = create_canonical_name(label)
    if type(items) is list:
        count = len(items)
    else:
        count = items.totalCount
    metric = f'{repo_name}_{state}_{item_type}_label_{canonical_label.lower()}'
    description = f'Count of {state} {item_type} on {repo_id} with label {label}'
    metrics = append_pushgateway_metrics(metrics, metric, count, description)

    count = count_repository_open_items_unassigned(items)
    metric = f'{repo_name}_{state}_{item_type}_label_{canonical_label.lower()}_unassigned'
    description = f'Count of unassigned {state} {item_type} on {repo_id} with label {label}'
    metrics = append_pushgateway_metrics(metrics, metric, count, description)

    days = get_github_metrics('no_activity_limit')
    count = len(filter_outdated_items(items, days))
    metric = f'{repo_name}_{state}_{item_type}_label_{canonical_label.lower()}_old'
    description = f'Count of old {state} {item_type} on {repo_id} with label {label}'
    metrics = append_pushgateway_metrics(metrics, metric, count, description)
    return metrics


def collect_repository_issues_by_label(
        session: Github, repo_id: str, metrics: dict, state: str) -> dict:
    for label in get_github_labels():
        issues = get_repository_issues(session, repo_id, f'state={state}', label)
        metrics = collect_repository_items_by_label(repo_id, metrics, issues, label, state,
                                                    'issues')
        pulls = filter_pulls_from_issues(issues)
        metrics = collect_repository_items_by_label(repo_id, metrics, pulls, label, state,
                                                    'pulls')
    return metrics


def process_open_items(repo_id: str, metrics: dict, items: list, type: str, suffix='') -> dict:
    repo_name = create_canonical_name(repo_id)
    days = get_github_metrics('no_activity_limit')
    outdated_items = filter_outdated_items(items, days)

    if suffix:
        # suffix is passed as a text for the metric description.
        # For the respective metric id it is used the last word of the suffix.
        metric_suffix = f'_{create_canonical_name(suffix.split()[-1])}'
    else:
        metric_suffix = ''

    if isinstance(items, list):
        count = len(items)
    else:
        count = items.totalCount
    description = f'Count of open {type} on {repo_id} {suffix}'
    metrics = append_pushgateway_metrics(
        metrics, f'{repo_name}_open_{type}{metric_suffix}', count, description)

    count = count_repository_open_items_unassigned(items)
    description = f'Count of unassigned open {type} on {repo_id} {suffix}'
    metrics = append_pushgateway_metrics(
        metrics, f'{repo_name}_unassigned_open_{type}{metric_suffix}', count, description)

    count = len(outdated_items)
    description = f'Count of old open {type} on {repo_id} {suffix}'
    metrics = append_pushgateway_metrics(
        metrics, f'{repo_name}_old_open_{type}{metric_suffix}', count, description)

    return metrics


def collect_repository_open_items(repo_id: str, metrics: dict, items: list, type: str) -> dict:
    metrics = process_open_items(repo_id, metrics, items, type, '')
    # Metrics based on filtered objects created by team members
    team_items = filter_repository_open_items_team(items)
    metrics = process_open_items(repo_id, metrics, team_items, type, 'filed by team')
    return metrics


def collect_repository_open_issues(session: Github, repo_id: str, metrics: dict) -> dict:
    open_issues = get_repository_issues(session, repo_id, 'state=open', '')
    return collect_repository_open_items(repo_id, metrics, open_issues, 'issues')


def collect_repository_open_pulls(session: Github, repo_id: str, metrics: dict) -> dict:
    open_pulls = get_repository_pulls(session, repo_id, 'state=open')
    return collect_repository_open_items(repo_id, metrics, open_pulls, 'pulls')


def get_workflows_runs_stats(repo: Repository) -> dict:
    workflows_metrics = get_github_metrics('workflows')
    runs_summary = {}
    for status in workflows_metrics['status']:
        query = repo.get_workflow_runs(status=status)
        runs_summary.update({status: query.totalCount})
    return runs_summary


def collect_workflows_runs_stats(repo: Repository) -> dict:
    repo_name = create_canonical_name(repo.name)
    runs_summary = get_workflows_runs_stats(repo)
    for status in runs_summary.keys():
        metric = f'{repo_name}_workflows_status'
        description = f'Count of {status} workflows runs on {repo_name}'
        value = runs_summary[status]
        print(f'{metric}: {value} - {description}')


def get_workflow_id_by_name(repo: Repository, name: str) -> int:
    workflows = repo.get_workflows()
    for workflow in workflows:
        if workflow.name == name:
            return workflow.id


def get_workflow_last_run_info(repo: Repository, name: str) -> int:
    workflow_id = get_workflow_id_by_name(repo, name)
    workflow = repo.get_workflow(workflow_id)
    runs = workflow.get_runs(status='completed')
    last_run = runs[0]
    workflow_info = {'status': last_run.status, 'conclusion': last_run.conclusion,
                     'created_at': last_run.created_at, 'updated_at': last_run.updated_at,
                     'html_url': last_run.html_url}
    return workflow_info


def collect_workflows_last_run_info(repo: Repository) -> int:
    workflows_metrics = get_github_metrics('workflows')
    repo_name = create_canonical_name(repo.name)
    for name in workflows_metrics['names']:
        workflow_info = get_workflow_last_run_info(repo, name)
        workflow_name = create_canonical_name(name)
        for info in workflow_info.keys():
            metric = f'{repo_name}_workflow_{workflow_name}_info'
            description = f'Count of {info} workflows runs on {repo_name}'
            value = workflow_info[info]
            print(f'{metric}: {value} - {description}')


def collect_workflows_information(session: Github, repo_id: str) -> dict:
    repo = get_repository_object(session, repo_id)
    collect_workflows_runs_stats(repo)
    collect_workflows_last_run_info(repo)


def collect_repository_metrics_prometheus(session: Github, repo_id: str) -> list:
    repo_name = create_canonical_name(repo_id)

    metrics = []
    for metric in get_github_metrics('repo'):
        if metric in ['contributors', 'events']:
            if metric == 'contributors':
                contributors = get_repository_contributors(session, repo_id)
                count = contributors.totalCount
            elif metric == 'events':
                events = get_repository_events(session, repo_id)
                count = events.totalCount
            description = f'Count of {metric} on {repo_id}'
            metrics = append_pushgateway_metrics(
                metrics, f'{repo_name}_{metric}', count, description)
        elif metric == 'general_info':
            metrics = collect_repository_info(session, repo_id, metrics)
        elif metric == 'issues_by_label':
            metrics = collect_repository_issues_by_label(session, repo_id, metrics, 'open')
        elif metric == 'created_pulls_by_timeframe':
            metrics = collect_created_pulls(session, repo_id, metrics)
        elif metric == 'created_issues_by_timeframe':
            metrics = collect_created_issues(session, repo_id, metrics)
        elif metric == 'open_issues':
            metrics = collect_repository_open_issues(session, repo_id, metrics)
        elif metric == 'open_pulls':
            metrics = collect_repository_open_pulls(session, repo_id, metrics)
        elif metric == 'pulls_lifetime_average':
            metrics = collect_pulls_lifetime_average(session, repo_id, metrics)
        elif metric == 'issues_lifetime_average':
            metrics = collect_issues_lifetime_average(session, repo_id, metrics)
        elif metric == 'workflows':
            collect_workflows_information(session, repo_id)
        else:
            print(f'Metric {metric} is not available.')
            continue
    return metrics


def push_metrics_prometheus(session: Github, org_id: str, repo_id: str) -> None:
    registry = create_pushgateway_registry()
    registry, org_repositories = collect_org_metrics_prometheus(session, org_id, registry)
    if repo_id == 'all':
        for repo in org_repositories:
            repo_metrics = collect_repository_metrics_prometheus(session, repo.full_name)
            registry = parse_repo_metrics(repo_metrics, registry)
    else:
        repo_metrics = collect_repository_metrics_prometheus(session, repo_id)
        registry = parse_repo_metrics(repo_metrics, registry)
    push_pushgateway_metrics(registry)


def print_results(results: list, object_type: str, args) -> str:
    if args.count:
        if type(results) is list:
            print(len(results))
        else:
            print(results.totalCount)
        exit(0)
    print_object_info_header(object_type)
    for item in results:
        print_object_info(object_type, item, args.org)


def print_lifetime_results(lifetime_info: dict, type: str, last_days: str) -> str:
    for state in ['closed', 'open']:
        count_key = f'{state}_count'
        count = lifetime_info[count_key]
        lifetime_key = f'{state}_lifetime'
        lifetime = lifetime_info[lifetime_key]
        hours = lifetime // 60
        days = lifetime // 1440
        if state == 'closed':
            suffix = f' within the last {last_days} days'
        else:
            suffix = ''
        print(f'{state} {type} lifetime average{suffix}: '
              f'{days} day(s) or {hours} hour(s) or {lifetime} minute(s) for {count} {type}')


def parse_arguments() -> ArgumentParser:
    parser = ArgumentParser(description='Collect Github Information.')
    parser.add_argument(
        '-o', '--org', action='store', default='ExampleOrg',
        help='The organization ID to be consulted.')
    parser.add_argument(
        '-r', '--repository', action='store', default='all',
        help='Repository name when required by a function.')
    parser.add_argument(
        '-a', '--action', action='store',
        choices=['list-org-repos', 'list-org-members', 'list-repo-contributors',
                 'list-repo-infos', 'list-repo-labels', 'list-repo-events',
                 'list-repo-issues', 'list-repo-old-issues', 'calc-repo-issues-lifetime',
                 'list-repo-pulls', 'list-repo-old-pulls', 'calc-repo-pulls-lifetime',
                 'push-metrics-prometheus'],
        help='Choose one of the available options.')
    parser.add_argument(
        '-c', '--count', action='store_true',
        help='Show the numbers only.')
    parser.add_argument(
        '-d', '--days', action='store', default='30',
        help='Number of days to filter older issues or pulls.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-f', '--filters', action='store', default='',
        help='Query filters accepted by the API: https://docs.github.com/en/rest/reference/')
    group.add_argument(
        '-l', '--labels', action='store', default='',
        help='Comma separated labels used to filter the results.')
    return parser.parse_args()


def main():
    args = parse_arguments()
    ORG = args.org
    REPOSITORY = args.repository
    ACTION = args.action
    FILTERS = args.filters
    LABELS = args.labels
    DAYS = int(args.days)

    ghs = create_github_session()

    if ACTION == 'list-org-repos':
        results = get_repositories_list(ghs, ORG)
        print_results(results, 'repository', args)
    elif ACTION == 'list-org-members':
        results = get_members_list(ghs, ORG, 'all')
        print_results(results, 'user', args)
    elif ACTION == 'list-repo-contributors':
        results = get_repository_contributors(ghs, REPOSITORY)
        print_results(results, 'user', args)
    elif ACTION == 'list-repo-events':
        results = get_repository_events(ghs, REPOSITORY)
        print_results(results, 'event', args)
    elif ACTION == 'list-repo-infos':
        repo_infos = get_repository_infos(ghs, REPOSITORY)
        for info in repo_infos.keys():
            print(f'{info},{repo_infos[info]}')
    elif ACTION == 'list-repo-issues':
        results = get_repository_issues(ghs, REPOSITORY, FILTERS, LABELS)
        print_results(results, 'issue', args)
    elif ACTION == 'list-repo-labels':
        results = get_repository_labels(ghs, REPOSITORY)
        print_results(results, 'label', args)
    elif ACTION == 'list-repo-labels-count':
        print("name,open_issues,closed_issues")
        for label in get_repository_labels(ghs, REPOSITORY):
            get_repository_label_usage_count(ghs, REPOSITORY, label.name)
    elif ACTION == 'list-repo-old-issues':
        results = get_repository_outdated_issues(ghs, REPOSITORY, DAYS)
        print_results(results, 'issue', args)
    elif ACTION == 'list-repo-pulls':
        results = get_repository_pulls(ghs, REPOSITORY, FILTERS)
        print_results(results, 'pull', args)
    elif ACTION == 'list-repo-old-pulls':
        results = get_repository_outdated_pulls(ghs, REPOSITORY, DAYS)
        print_results(results, 'pull', args)
    elif ACTION == 'list-repo-recent-pulls':
        results = get_repository_created_pulls(ghs, REPOSITORY, DAYS)
        print_results(results, 'pull', args)
    elif ACTION == 'calc-repo-issues-lifetime':
        lifetime_info = dict()
        closed_issues = get_repository_issues(ghs, REPOSITORY,
                                              'state=closed,sort=closed,direction=desc', '')
        lifetime_info = get_items_lifetime_average(closed_issues, DAYS,
                                                   lifetime_info, 'closed')
        open_issues = get_repository_issues(ghs, REPOSITORY,
                                            'state=open,sort=opened,direction=desc', '')
        lifetime_info = get_items_lifetime_average(closed_issues, DAYS,
                                                   lifetime_info, 'closed')
        lifetime_info = get_items_lifetime_average(open_issues, DAYS,
                                                   lifetime_info, 'open')
        print_lifetime_results(lifetime_info, 'issues', DAYS)
    elif ACTION == 'calc-repo-pulls-lifetime':
        lifetime_info = dict()
        closed_pulls = get_repository_pulls(ghs, REPOSITORY,
                                            'state=closed,sort=closed,direction=desc')
        lifetime_info = get_items_lifetime_average(closed_pulls, DAYS,
                                                   lifetime_info, 'closed')
        open_pulls = get_repository_pulls(ghs, REPOSITORY,
                                          'state=open,sort=opened,direction=desc')
        lifetime_info = get_items_lifetime_average(open_pulls, DAYS,
                                                   lifetime_info, 'open')
        print_lifetime_results(lifetime_info, 'pulls', DAYS)
    elif ACTION == 'push-metrics-prometheus':
        push_metrics_prometheus(ghs, ORG, REPOSITORY)
        print("Metrics successfully sent!")
    else:
        print("Action not found!")


if __name__ == '__main__':
    main()
