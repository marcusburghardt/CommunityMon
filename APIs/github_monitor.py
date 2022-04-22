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
from ast import arg
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
                    list-repo-events, list-repo-infos, list-repo-issues, list-repo-old-issues, \
                    list-repo-pulls, list-repo-old-pulls, calc-repo-pulls-lifetime, \
                    push-metrics-prometheus')
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

def get_repository_events(session, repo_id):
    repo = get_repository_object(session, repo_id)
    return repo.get_events()

def get_repository_infos(session, repo_id) -> dict:
    repo = get_repository_object(session, repo_id)
    infos = { 'forks_count':repo.forks_count, 'stargazers_count':repo.stargazers_count,
              'subscribers_count':repo.subscribers_count, 'archived':repo.archived,
              'private':repo.private, 'open_issues_count':repo.open_issues_count, }
    return infos

def get_repository_issues(session, repo_id, filters_string, labels_string):
    repo = get_repository_object(session, repo_id)
    labels_list = []
    if labels_string:
        labels_list = create_list_from_string(labels_string, ',')
        return repo.get_issues(labels=labels_list)
    if filters_string:
        filters_dict = create_dict_from_string(filters_string, ',')
        filters = parse_filters_string(filters_dict, 'issue')
        milestone = get_milestone_by_title(repo, filters['milestone'])
        assignee = get_user_by_login(session, filters['assignee'])
        filtered_issues = repo.get_issues(state=filters['state'],
                                          assignee=assignee,
                                          milestone=milestone)
        return filtered_issues
    else:
        return repo.get_issues()

def get_repository_old_issues(session, repo_id, days):
    filter_string = "state=open,assignee=none"
    open_issues_without_assignee = get_repository_issues(session, repo_id, filter_string, '')
    old_open_issues = []
    old_date = get_old_date(days)
    for issue in open_issues_without_assignee:
        if issue.updated_at < old_date:
            old_open_issues.append(issue)
    return old_open_issues

def get_repository_pulls(session, repo_id, filters_string):
    repo = get_repository_object(session, repo_id)
    if filters_string:
        filters_dict = create_dict_from_string(filters_string, ';')
        filters = parse_filters_string(filters_dict, 'pull')
        filtered_pulls = repo.get_pulls(state=filters['state'])
        return filtered_pulls
    else:
        return repo.get_pulls()

def get_repository_old_pulls(session, repo_id, days):
    filter_string = "state=open"
    open_pulls = get_repository_pulls(session, repo_id, filter_string)
    old_open_pulls = []
    old_date = get_old_date(days)
    for pull in open_pulls:
        if pull.updated_at < old_date:
            old_open_pulls.append(pull)
    return old_open_pulls

def get_repository_created_pulls(session, repo_id, days):
    filter_string = "state=all"
    open_pulls = get_repository_pulls(session, repo_id, filter_string)
    recent_pulls = []
    old_date = get_old_date(days)
    for pull in open_pulls:
        if pull.created_at < old_date:
            break
        recent_pulls.append(pull)
    return recent_pulls

def get_pulls_lifetime_average(session, repo_id, days) -> int:
    closed_pulls_list = get_repository_pulls(session, repo_id, 'state=closed')
    # INFO: Getting all closed pulls can hit the API limits depending on the project
    # activity. Here we limit the last (days) closed pulls since they are ordered by
    # closed time from the API.
    old_date = get_old_date(days)
    pulls_lifetime_in_minutes = 0
    processed_pulls_count = 0
    for pull in closed_pulls_list:
        if pull.closed_at < old_date:
            break
        pull_delta_time = get_delta_time(pull.created_at, pull.closed_at, 'm')
        pulls_lifetime_in_minutes += pull_delta_time
        processed_pulls_count += 1
        if args.verbose:
            print("PR#%s - Created: %s, Updated: %s, Closed: %s, Lifetime (Min): %s" %
                 (pull.number, pull.created_at, pull.updated_at, pull.closed_at,
                  pull_delta_time))
    return processed_pulls_count, pulls_lifetime_in_minutes//processed_pulls_count

def collect_org_metrics_prometheus(session, org_id, registry):
    org_members = get_members_list(session, org_id, 'all')
    org_admins = get_members_list(session, org_id, 'admin')
    org_repositories = get_repositories_list(session, org_id)
    registry = create_pushgateway_gauge_metric(org_id+'_org_members',
                                               'Count of members on '+org_id+' org',
                                                org_members.totalCount, registry)
    registry = create_pushgateway_gauge_metric(org_id+'_org_admins',
                                               'Count of admins on '+org_id+' org',
                                                org_admins.totalCount, registry)
    registry = create_pushgateway_gauge_metric(org_id+'_org_repositories',
                                               'Count of repositories on '+org_id+' org',
                                                org_repositories.totalCount, registry)
    return registry, org_repositories

def collect_repository_issues_by_label(session, repo_id, metrics):
    labels = create_list_from_string(get_github_labels(),',')
    repo_name = create_canonical_name(repo_id)
    for label in labels:
        canonical_name = create_canonical_name(label)
        issues = get_repository_issues(session, repo_id, 'state=open', label)
        metrics.append({'metric':repo_name+'_open_issues_label_'+canonical_name.lower(),
                        'value':issues.totalCount,
                        'description':'Count of open issues on '+repo_id+' with label '+label })

    return metrics

def collect_repository_metrics_prometheus(session, repo_id, days) -> list:
    metrics = []
    metrics = collect_repository_issues_by_label(session, repo_id, metrics)
    repo_name=create_canonical_name(repo_id)
    if args.verbose:
        print(repo_name)
    repo_infos = get_repository_infos(session, repo_id)
    for info in repo_infos.keys():
        metrics.append({'metric':repo_name+'_'+info,
                        'value':repo_infos[info],
                        'description':'Count of '+info+' on '+repo_id })
    
    contributors = get_repository_contributors(session, repo_id)
    metrics.append({'metric':repo_name+'_contributors',
                    'value':contributors.totalCount,
                    'description':'Count of contributors on '+repo_id })
    events = get_repository_events(session, repo_id)
    metrics.append({'metric':repo_name+'_events',
                    'value':events.totalCount,
                    'description':'Count of events on '+repo_id })
    open_pulls = get_repository_pulls(session, repo_id, 'state=open')
    metrics.append({'metric':repo_name+'_open_pulls',
                    'value':open_pulls.totalCount,
                    'description':'Count of open pulls on '+repo_id })
    old_open_issues = get_repository_old_issues(session, repo_id, days)
    metrics.append({'metric':repo_name+'_old_open_issues',
                    'value':len(old_open_issues),
                    'description':'Count of old ('+str(days)+'d) open issues on '+repo_id })
    old_open_pulls = get_repository_old_pulls(session, repo_id, days)
    metrics.append({'metric':repo_name+'_old_open_pulls',
                    'value':len(old_open_pulls),
                    'description':'Count of old ('+str(days)+'d) open pulls on '+repo_id })
    closed_pulls_count, pulls_lifetime = get_pulls_lifetime_average(session, repo_id, 90)
    metrics.append({'metric':repo_name+'_pulls_lifetime_average',
                    'value':pulls_lifetime,
                    'description':'Average lifetime of closed pulls from last 90 days on '+repo_id })
    metrics.append({'metric':repo_name+'_closed_pulls_90days',
                    'value':closed_pulls_count,
                    'description':'Number of closed pulls from last 90 days on '+repo_id })
    recent_pulls_count = get_repository_created_pulls(session, repo_id, 90)
    metrics.append({'metric':repo_name+'_created_pulls_90days',
                    'value':len(recent_pulls_count),
                    'description':'Number of created pulls from last 90 days on '+repo_id })
    return metrics

def push_metrics_prometheus(session, org_id, days):
    registry = create_pushgateway_registry()
    registry, org_repositories = collect_org_metrics_prometheus(session, org_id, registry)
    if REPOSITORY == 'all':
        for repo in org_repositories:
            repo_metrics = collect_repository_metrics_prometheus(session, repo.full_name, days)
            registry = parse_repo_metrics(repo_metrics, registry)
    else:
        repo_metrics = collect_repository_metrics_prometheus(session, REPOSITORY, days)
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
            print('%s: %s' % (info, repo_infos[info]))
    elif ACTION == 'list-repo-issues':
        results = get_repository_issues(ghs, REPOSITORY, FILTERS, LABELS)
        print_results(results, 'issue')
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
    elif ACTION == 'calc-repo-pulls-lifetime':
        pulls_count, average_in_minutes = get_pulls_lifetime_average(ghs, REPOSITORY, DAYS)
        print("Pulls lifetime average for the last %s days: %s minutes for %s pulls" %
             (DAYS, average_in_minutes, pulls_count))
    elif ACTION == 'push-metrics-prometheus':
        push_metrics_prometheus(ghs, ORG, DAYS)
        print("Metrics successfully sent!")
    else:
        print("Action not found!")

if __name__ == '__main__':
    main()