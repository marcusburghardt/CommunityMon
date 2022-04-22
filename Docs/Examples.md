# Queries
## Organizations
List the organization repositories:
> github_monitor.py -o ComplianceAsCode -a list-org-repos

List the organization members and respective roles:
> github_monitor.py -o ComplianceAsCode -a list-org-members

## Repositories
List basic information from the `ComplianceAsCode/content` repository:
> github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a list-repo-infos

### Issues and Pulls
Simple query for open issues in `ComplianceAsCode/content` repository:
> github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a list-repo-issues

It is also possible to refine the query with filters and labels:
> github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a list-repo-pulls -f "state=open"

> github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a list-repo-issues -l "productization-issue"

These are the available filters for issues:
 - state: open, closed, or all
 - milestone: milestone title or “none” or “*”
 - assignee: login name
 - labels: comma separated list of labels. If multiple labels are provided, only issues labeled with all of them will be returned.

These are the available filters for pulls:
 - state: open, closed, or all
 - milestone: milestone title or “none” or “*”
 - assignee: login name
 - labels: comma separated list of labels. If multiple labels are provided, only issues labeled with all of them will be returned.

### Events
List the repository events from the last 24 hours:
> github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a list-repo-events
