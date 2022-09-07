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

import argparse
from github import Github
from common import *
from prometheus_pushgw import *

parser = argparse.ArgumentParser(description='Collect Github Information.')
parser.add_argument('-o', '--org', action='store', default='ExampleOrg',
                    help='The organization ID to be consulted.')
parser.add_argument('-r', '--repository', action='store', default='all',
                    help='Repository name when required by a function.')
parser.add_argument('-a', '--action', action='store', default='list-org-repos',
                    help='list-org-repos, list-org-members, list-repo-contributors, \
                    list-repo-events, list-repo-infos, list-repo-issues, list-repo-labels, \
                    list-repo-old-issues, list-repo-pulls, list-repo-old-pulls, \
                    calc-repo-issues-lifetime, calc-repo-pulls-lifetime, push-metrics-prometheus')
parser.add_argument('-c', '--count', action='store_true',
                    help='Show the numbers only.')
parser.add_argument('-d', '--days', action='store', default='30',
                    help='Number of days to filter older issues or pulls.')
group = parser.add_mutually_exclusive_group()
group.add_argument('-f', '--filters', action='store', default='',
                    help='Query filters accepted by the API: https://docs.github.com/en/rest/reference/')
group.add_argument('-l', '--labels', action='store', default='',
                    help='Comma separated labels used to filter the results.')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='Show some extra information during the actions.')

args = parser.parse_args()
ORG = args.org
REPOSITORY = args.repository
ACTION = args.action
FILTERS = args.filters
LABELS = args.labels
DAYS = int(args.days)

def create_github_session():
    return Github(get_github_token())

def filter_created_items_by_lifetime(items, days):
    recent_items = []
    old_date = get_old_date(days)
    for item in items:
        if item.created_at < old_date:
            break
        recent_items.append(item)
    return recent_items

def filter_items_by_owner(items, owners) -> int:
    count = 0
    for item in items:
        if item.user.login in owners:
            count += 1
    return count

def filter_outdated_items(items, days) -> list:
    old_open_items = []
    old_date = get_old_date(days)
    for item in items:
        if item.updated_at < old_date:
            old_open_items.append(item)
    return old_open_items

def filter_repository_open_items_team(items) -> list:
    team_members = get_github_metrics('team')
    open_items_team = []
    for item in items:
        if item.user.login in team_members:
            open_items_team.append(item)
    return open_items_team

def filter_repository_open_items_unassigned(items) -> int:
    count = 0
    for item in items:
        if item.assignee is None:
            count += 1
    return count

def get_organization_object(session, org_id):
    return session.get_organization(org_id)

def get_repository_object(session, repo_id):
    return session.get_repo(repo_id)

def get_milestone_by_title(repo, milestone_title):
    if milestone_title in ['none', '*']:
        return milestone_title
    milestones = repo.get_milestones()
    for item in milestones:
        if item.title == milestone_title:
            return item
    print("The milestone title was not found!")
    exit(1)

def get_user_by_login(session, user_login):
    if user_login in ['none', '*']:
        return user_login
    return session.get_user(login=user_login)

def get_members_list(session, org_id, role):
    org = get_organization_object(session, org_id)
    return org.get_members(role=role)

def get_repositories_list(session, org_id):
    org = get_organization_object(session, org_id)
    return org.get_repos(type=REPOSITORY)

def get_repository_contributors(session, repo_id):
    repo = get_repository_object(session, repo_id)
    return repo.get_contributors()

def get_repository_created_issues(session, repo_id, days, filter_string):
    open_issues = get_repository_issues(session, repo_id, filter_string, '')
    return filter_created_items_by_lifetime(open_issues, days)

def get_repository_created_pulls(session, repo_id, days, filter_string):
    open_pulls = get_repository_pulls(session, repo_id, filter_string)
    return filter_created_items_by_lifetime(open_pulls, days)

def get_repository_events(session, repo_id):
    repo = get_repository_object(session, repo_id)
    return repo.get_events()

def get_repository_infos(session, repo_id: str) -> dict:
    repo = get_repository_object(session, repo_id)
    labels_count = get_repository_labels(session, repo_id)
    infos = { 'forks_count':repo.forks_count, 'stargazers_count':repo.stargazers_count,
              'subscribers_count':repo.subscribers_count, 'archived':repo.archived,
              'private':repo.private, 'open_issues_count':repo.open_issues_count,
              'labels_count':labels_count.totalCount }
    return infos

def get_repository_issues(session, repo_id, filters_string, labels_string):
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

def get_repository_label_count(session, repo_id, label):
    filter_string = 'state=all'
    issues = get_repository_issues(session, repo_id, filter_string, label)
    count_open = len([issues for issue in issues if issue.state == 'open'])
    count_closed = len([issues for issue in issues if issue.state == 'closed'])
    print(f'{label},{count_open},{count_closed}')

def get_repository_labels(session, repo_id):
    repo = get_repository_object(session, repo_id)
    return repo.get_labels()

def get_repository_old_issues(session, repo_id, days):
    filter_string = "state=open"
    open_issues = get_repository_issues(session, repo_id, filter_string, '')
    return filter_outdated_items(open_issues, days)

def get_repository_old_pulls(session, repo_id, days):
    filter_string = "state=open"
    open_pulls = get_repository_pulls(session, repo_id, filter_string)
    return filter_outdated_items(open_pulls, days)

def get_repository_pulls(session, repo_id, filters_string):
    repo = get_repository_object(session, repo_id)
    if filters_string:
        filters_dict = create_dict_from_string(filters_string, ',')
        filters = parse_filters_string(filters_dict, 'pull')
        filtered_pulls = repo.get_pulls(state=filters['state'], sort=filters['sort'],
                                        direction=filters['direction'])
        return filtered_pulls
    else:
        return repo.get_pulls()

def get_items_lifetime_average(closed_items, days: str) -> dict:
    # INFO: Getting info from all closed pulls can hit the API limits depending on the
    # project activity. Here we limit the last (days) closed pulls since they are ordered
    # by closed time from the API.
    old_date = get_old_date(days)
    processed_items = 0
    lifetime_in_minutes = 0
    lifetime = 0

    team_members = get_github_metrics('team')
    processed_items_team = 0
    lifetime_in_minutes_team = 0
    lifetime_team = 0

    for item in closed_items:
        if item.closed_at < old_date:
            break
        delta_time = get_delta_time(item.created_at, item.closed_at, 'm')
        lifetime_in_minutes += delta_time
        processed_items += 1
        if item.user.login in team_members:
            lifetime_in_minutes_team += delta_time
            processed_items_team += 1
        if args.verbose:
            print(f'PR#{item.number} - Created: {item.created_at}, Updated: {item.updated_at},\
                  Closed: {item.closed_at}, Lifetime (Min): {delta_time}')
    if processed_items:
        lifetime = lifetime_in_minutes//processed_items
    else:
        if args.verbose:
            print(f'It was not found closed items within last {days} days')
    if processed_items_team:
        lifetime_team = lifetime_in_minutes_team//processed_items_team
    lifetime_info = {'count': processed_items,
                    'lifetime': lifetime,
                    'count_team': processed_items_team,
                    'lifetime_team': lifetime_team}
    return lifetime_info

def get_issues_lifetime_average(closed_issues, days: str) -> dict:
    return get_items_lifetime_average(closed_issues, days)

def get_pulls_lifetime_average(closed_pulls, days: str) -> dict:
    return get_items_lifetime_average(closed_pulls, days)

def collect_created_items(repo_id, metrics: dict, created_items, timeframe: str, type: str) -> dict:
    repo_name = create_canonical_name(repo_id)
    metric = f'{repo_name}_created_{type}_{timeframe}days'
    description = f'Number of created {type} within last {timeframe} days on {repo_id}'
    metrics = append_pushgateway_metrics(metrics, metric, len(created_items), description)
    # By team
    count = collect_created_issues_by_team(created_items)
    metric = f'{repo_name}_created_{type}_by_team_{timeframe}days'
    description = f'Number of {type} created by the team within last {timeframe} days on {repo_id}'
    metrics = append_pushgateway_metrics(metrics, metric, count, description)
    return metrics

def collect_created_issues_by_team(issues) -> int:
    team_members = get_github_metrics('team')
    return filter_items_by_owner(issues, team_members)

def collect_created_issues(session, repo_id: str, metrics: dict) -> dict:
    filter_string = "state=all"
    for timeframe in get_github_metrics('timeframe'):
        created_issues = get_repository_created_issues(session, repo_id, timeframe, filter_string)
        metrics = collect_created_items(repo_id, metrics, created_issues, timeframe, 'issues')
    return metrics

def collect_created_pulls_by_team(pulls) -> int:
    team_members = get_github_metrics('team')
    return filter_items_by_owner(pulls, team_members)

def collect_created_pulls(session, repo_id: str, metrics: dict) -> dict:
    filter_string = "state=all"
    for timeframe in get_github_metrics('timeframe'):
        created_pulls = get_repository_created_pulls(session, repo_id, timeframe, filter_string)
        metrics = collect_created_items(repo_id, metrics, created_pulls, timeframe, 'pulls')
    return metrics

def collect_org_metrics_prometheus(session, org_id: str, registry):
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
            if args.verbose:
                print(f'Metric {metric} is not available.')
            continue
        registry = create_pushgateway_gauge_metric(f'{org_id}_org_{metric}',
                                                   f'Count of {metric} on {org_id} org',
                                                    count, registry)
    return registry, org_repositories

def collect_item_lifetime_average(repo_id: str, metrics: dict, lifetime_info,
                                  timeframe, item) -> dict:
    repo_name = create_canonical_name(repo_id)
    # count
    metric = f'{repo_name}_closed_{item}_{timeframe}days'
    description = f'Number of closed {item} from last {timeframe} days on {repo_id}'
    metrics = append_pushgateway_metrics(metrics, metric,
                                         lifetime_info['count'], description)
    # count team
    metric = f'{repo_name}_closed_{item}_{timeframe}days_team'
    description = f'Number of closed team {item} from last {timeframe} days on {repo_id}'
    metrics = append_pushgateway_metrics(metrics, metric,
                                         lifetime_info['count_team'], description)
    # lifetime
    metric = f'{repo_name}_{item}_lifetime_average_{timeframe}days'
    description = f'Average lifetime of closed {item} from last {timeframe} days on {repo_id}'
    metrics = append_pushgateway_metrics(metrics, metric,
                                         lifetime_info['lifetime'], description)
    # lifetime team
    metric = f'{repo_name}_{item}_lifetime_average_{timeframe}days_team'
    description = f'Average lifetime of closed team {item} from last {timeframe} days on {repo_id}'
    metrics = append_pushgateway_metrics(metrics, metric,
                                         lifetime_info['lifetime_team'], description)
    return metrics

def collect_issues_lifetime_average(repo_id: str, metrics: dict, closed_issues) -> dict:
    for timeframe in get_github_metrics('timeframe'):
        lifetime_info = get_issues_lifetime_average(closed_issues, timeframe)
        metrics = collect_item_lifetime_average(repo_id, metrics, lifetime_info, timeframe,
                                                'issues')
    return metrics

def collect_pulls_lifetime_average(repo_id: str, metrics: dict, closed_pulls) -> dict:
    for timeframe in get_github_metrics('timeframe'):
        lifetime_info = get_pulls_lifetime_average(closed_pulls, timeframe)
        metrics = collect_item_lifetime_average(repo_id, metrics, lifetime_info, timeframe,
                                                'pulls')
    return metrics

def collect_repository_info(session, repo_id: str, metrics: dict) -> dict:
    repo_name = create_canonical_name(repo_id)
    repo_infos = get_repository_infos(session, repo_id)
    for repo_info in repo_infos.keys():
        description = f'Count of {repo_info} on {repo_id}'
        metrics = append_pushgateway_metrics(metrics, f'{repo_name}_{repo_info}',
                                             repo_infos[repo_info], description)
    return metrics

def collect_repository_items_by_label(repo_id: str, metrics: dict, items, label: str, state: str,
                                      type: str) -> dict:
    repo_name = create_canonical_name(repo_id)
    canonical_label = create_canonical_name(label)
    metric = f'{repo_name}_{state}_{type}_label_{canonical_label.lower()}'
    description = f'Count of {state} {type} on {repo_id} with label {label}'
    metrics = append_pushgateway_metrics(metrics, metric, items.totalCount, description)
    return metrics

def collect_repository_issues_by_label(session, repo_id: str, metrics: dict, state: str) -> dict:
    for label in get_github_labels():
        issues = get_repository_issues(session, repo_id, f'state={state}', label)
        metrics = collect_repository_items_by_label(repo_id, metrics, issues, label, state, 'issues')
    return metrics

def collect_repository_open_items(repo_id: str, metrics: dict, items, type: str) -> dict:
    repo_name = create_canonical_name(repo_id)
    count = items.totalCount

    description = f'Count of open {type} on {repo_id}'
    metrics = append_pushgateway_metrics(metrics, f'{repo_name}_open_{type}',
                                         count, description)

    count = filter_repository_open_items_unassigned(items)
    description = f'Count of unassigned open {type} on {repo_id}'
    metrics = append_pushgateway_metrics(metrics, f'{repo_name}_unassigned_open_{type}',
                                         count, description)

    days = get_github_metrics('no_activity_limit')
    count = len(filter_outdated_items(items, days))
    description = f'Count of old open {type} on {repo_id}'
    metrics = append_pushgateway_metrics(metrics, f'{repo_name}_old_open_{type}',
                                         count, description)

    # Metrics restricted to the team members
    team_items = filter_repository_open_items_team(items)
    description_team = f'Count of open {type} reported by the team on {repo_id}'
    metrics = append_pushgateway_metrics(metrics, f'{repo_name}_open_{type}_team',
                                         len(team_items), description_team)

    count = filter_repository_open_items_unassigned(team_items)
    description_team = f'Count of unassigned open {type} on {repo_id}'
    metrics = append_pushgateway_metrics(metrics, f'{repo_name}_unassigned_open_{type}_team',
                                         count, description_team)

    days = get_github_metrics('no_activity_limit')
    count = len(filter_outdated_items(team_items, days))
    description_team = f'Count of old open {type} on {repo_id}'
    metrics = append_pushgateway_metrics(metrics, f'{repo_name}_old_open_{type}_team',
                                         count, description_team)
    return metrics

def collect_repository_open_issues(session, repo_id: str, metrics: dict) -> dict:
    open_issues = get_repository_issues(session, repo_id, 'state=open', '')
    return collect_repository_open_items(repo_id, metrics, open_issues, 'issues')

def collect_repository_open_pulls(session, repo_id: str, metrics: dict) -> dict:
    open_pulls = get_repository_pulls(session, repo_id, 'state=open')
    return collect_repository_open_items(repo_id, metrics, open_pulls, 'pulls')

def collect_repository_metrics_prometheus(session, repo_id) -> list:
    repo_name=create_canonical_name(repo_id)
    if args.verbose:
        print(repo_name)

    metrics = []
    for metric in get_github_metrics('repo'):
        if args.verbose:
            print(metric)
        if metric in ['contributors', 'events']:
            if metric == 'contributors':
                contributors = get_repository_contributors(session, repo_id)
                count = contributors.totalCount
            elif metric == 'events':
                events = get_repository_events(session, repo_id)
                count = events.totalCount
            description = f'Count of {metric} on {repo_id}'
            metrics = append_pushgateway_metrics(metrics, f'{repo_name}_{metric}', count, description)
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
            closed_pulls_list = get_repository_pulls(session, repo_id,
                                                     'state=closed,sort=closed,direction=desc')
            metrics = collect_pulls_lifetime_average(repo_id, metrics, closed_pulls_list)
        elif metric == 'issues_lifetime_average':
            closed_issues_list = get_repository_issues(session, repo_id,
                                                       'state=closed,sort=closed,direction=desc',
                                                       '')
            metrics = collect_issues_lifetime_average(repo_id, metrics, closed_issues_list)
        else:
            if args.verbose:
                print(f'Metric {metric} is not available.')
            continue
    return metrics

def push_metrics_prometheus(session, org_id):
    registry = create_pushgateway_registry()
    registry, org_repositories = collect_org_metrics_prometheus(session, org_id, registry)
    if REPOSITORY == 'all':
        for repo in org_repositories:
            repo_metrics = collect_repository_metrics_prometheus(session, repo.full_name)
            registry = parse_repo_metrics(repo_metrics, registry)
    else:
        repo_metrics = collect_repository_metrics_prometheus(session, REPOSITORY)
        registry = parse_repo_metrics(repo_metrics, registry)
    push_pushgateway_metrics(registry)

def print_results(results, object_type=''):
    if args.count:
        if type(results) is list:
            print(len(results))
        else:
            print(results.totalCount)
        exit(0)
    print_object_info_header(object_type)
    for item in results:
        print_object_info(object_type, item, ORG)

def main():
    ghs = create_github_session()

    if ACTION == 'list-org-repos':
        results = get_repositories_list(ghs, ORG)
        print_results(results, 'repository')
    elif ACTION == 'list-org-members':
        results = get_members_list(ghs, ORG, 'all')
        print_results(results, 'user')
    elif ACTION == 'list-repo-contributors':
        results = get_repository_contributors(ghs, REPOSITORY)
        print_results(results, 'user')
    elif ACTION == 'list-repo-events':
        results = get_repository_events(ghs, REPOSITORY)
        print_results(results, 'event')
    elif ACTION == 'list-repo-infos':
        repo_infos = get_repository_infos(ghs, REPOSITORY)
        for info in repo_infos.keys():
            print(f'{info},{repo_infos[info]}')
    elif ACTION == 'list-repo-issues':
        results = get_repository_issues(ghs, REPOSITORY, FILTERS, LABELS)
        print_results(results, 'issue')
    elif ACTION == 'list-repo-labels':
        results = get_repository_labels(ghs, REPOSITORY)
        print_results(results, 'label')
    elif ACTION == 'list-repo-labels-count':
        print("name,open_issues,closed_issues")
        for label in get_repository_labels(ghs, REPOSITORY):
            get_repository_label_count(ghs, REPOSITORY, label.name)
    elif ACTION == 'list-repo-old-issues':
        results = get_repository_old_issues(ghs, REPOSITORY, DAYS)
        print_results(results, 'issue')
    elif ACTION == 'list-repo-pulls':
        results = get_repository_pulls(ghs, REPOSITORY, FILTERS)
        print_results(results, 'pull')
    elif ACTION == 'list-repo-old-pulls':
        results = get_repository_old_pulls(ghs, REPOSITORY, DAYS)
        print_results(results, 'pull')
    elif ACTION == 'list-repo-recent-pulls':
        results = get_repository_created_pulls(ghs, REPOSITORY, DAYS)
        print_results(results, 'pull')
    elif ACTION == 'calc-repo-issues-lifetime':
        closed_issues = get_repository_issues(ghs, REPOSITORY,
                                             'state=closed,sort=closed,direction=desc','')
        lifetime_info = get_issues_lifetime_average(closed_issues, DAYS)
        print(f'Issues lifetime average for the last {DAYS} days: {lifetime_info["lifetime"]} minutes for {lifetime_info["count"]} issues')
    elif ACTION == 'calc-repo-pulls-lifetime':
        closed_pulls = get_repository_pulls(ghs, REPOSITORY,
                                            'state=closed,sort=closed,direction=desc')
        lifetime_info = get_pulls_lifetime_average(closed_pulls, DAYS)
        print(f'Pulls lifetime average for the last {DAYS} days: {lifetime_info["lifetime"]} minutes for {lifetime_info["count"]} pulls')
    elif ACTION == 'push-metrics-prometheus':
        push_metrics_prometheus(ghs, ORG)
        print("Metrics successfully sent!")
    else:
        print("Action not found!")

if __name__ == '__main__':
    main()
