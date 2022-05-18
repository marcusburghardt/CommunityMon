#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
This file is used to accommodate common functions which are relevant
for multiple APIs.

Author: Marcus Burghardt - https://github.com/marcusburghardt
"""

import configparser
import os

root_path = os.path.dirname(os.path.realpath(__file__))
CONF_FILE=f"{root_path}/apis.conf"

def create_canonical_name(raw_string):
    canonical_name=raw_string.replace('/','_')
    for special_char in '-. ':
        canonical_name=canonical_name.replace(special_char,'')
    return canonical_name

def create_dict_from_string(string, delimiter):
    return dict(item.split("=") for item in string.split(delimiter))

def create_list_from_string(string, delimiter):
    return string.split(delimiter)

def get_github_token():
    github_creds_file = get_parameter_value(CONF_FILE, 'GITHUB', 'creds_file')
    return get_parameter_value(github_creds_file, "DEFAULT", "github_token")

def get_github_labels():
    return get_parameter_value(CONF_FILE, 'GITHUB', 'labels')

def get_delta_time(start_date, end_date, unit):
    delta_time = end_date - start_date
    seconds = (delta_time.days*86400)+delta_time.seconds
    if unit == 'm': return seconds//60
    elif unit == 'h': return seconds//60//60
    elif unit == 'd': return delta_time.days
    else: return delta_time.seconds

def get_old_date(days):
    from datetime import datetime, timedelta
    now = datetime.now()
    return now - timedelta(days=days)

def get_parameter_value(config_file, section, parameter):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config[section][parameter]

def parse_filters_string(filters_dict, object_type=''):
    if object_type == 'issue':
        filters = { 'state':'open', 'assignee':'none', 'milestone':'none' }
    elif object_type == 'pull':
        filters = { 'state':'open', 'sort':'created' }
    for parameter in filters_dict.keys():
        if not parameter in filters.keys():
            print('Invalid filter')
            exit()
        filters[parameter] = filters_dict[parameter]
    return filters

def print_object_info_header(object_type):
    if object_type == 'repository':
        print('%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s' %
            ('repoName', 'repoFullName', 'repoId', 'repoUrl', 'private',
              'owner', 'ownerUrl', 'forks_count', 'stargazers_count', 
              'open_issues_count', 'subscribers_count', 'created_at',
              'pushed_at', 'updated_at', 'private'))
    elif object_type == 'user':
        print('%s,%s,%s,%s,%s,%s,%s,%s' % 
            ('user', 'name', 'email', 'userUrl', 'membershipState',
             'organization', 'organizationRole', 'contributions'))
    elif object_type in ['issue', 'pull']:
        print('%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s' % 
            ('number', 'state', 'issueUrl', 'createdAt', 'updatedAt', 'closedAt',
             'lifetime', 'milestone', 'reporter', 'assignee', 'title'))
    elif object_type == 'event':
        print('%s,%s,%s' %
            ('actor', 'eventType', 'createdAt'))
    else:
        print('itemName')

def print_object_info(object_type, item, org):
    if object_type == 'repository':
        print('%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s' % 
            (item.name, item.full_name, item.id, item.html_url, item.private,
             item.owner.login, item.owner.html_url, item.forks_count, 
             item.stargazers_count, item.open_issues_count, item.subscribers_count,
             item.created_at, item.pushed_at, item.updated_at, item.private))
    elif object_type == 'user':
        try:
            membership = item.get_organization_membership(org)
            print('%s,%s,%s,%s,%s,%s,%s,%s' %
                (item.login, membership.user.name, membership.user.email, membership.user.url,
                membership.state, membership.organization.login, membership.role,
                item.contributions))
        except:
            print('%s,-,-,%s,-,-,-,%s' % (item.login, item.html_url, item.contributions))
    elif object_type == 'event':
        print('%s,%s,%s' %
            (item.actor.login, item.type, item.created_at))
    elif object_type in ['issue', 'pull']:
        assignee = None
        milestone = None
        if item.assignee:
            assignee = item.assignee.login
        if item.milestone:
            milestone = item.milestone.title
        if item.closed_at:
            end_date = item.closed_at
        else:
            end_date = item.updated_at
        lifetime = get_delta_time(item.created_at, end_date, 'm')
        print('%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s' %
            (item.number, item.state, item.html_url, item.created_at, item.updated_at,
             item.closed_at, lifetime, milestone, item.user.login, assignee, item.title))
    else:
        print(item)
