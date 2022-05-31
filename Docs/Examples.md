# Queries
## Organizations
List the organization repositories:
```shell
github_monitor.py -o ComplianceAsCode -a list-org-repos
```

List the organization members and respective roles:
```shell
github_monitor.py -o ComplianceAsCode -a list-org-members
```

## Repositories
List basic information from the `ComplianceAsCode/content` repository:
```shell
github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a list-repo-infos
```
List all contributors for the `ComplianceAsCode/content` repository, ordered by direct contributions:
```shell
github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a list-repo-contributors
```

### Issues and Pulls
Simple query for open issues in `ComplianceAsCode/content` repository:
```shell
github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a list-repo-issues
```

It is also possible to refine the query with filters and labels:
```shell
github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a list-repo-pulls -f "state=open"
github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a list-repo-issues -l "productization-issue"
```

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

#### Old Issues and Pulls
It is also possible to list Issues or Pulls which are not updated within n days. The following queries will show item not updated within last 15 days:
```shell
./github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a list-repo-old-issues -d 15
./github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a list-repo-old-pulls -d 15
```

#### Issues and PRs Lifetime
There an interesting metric where the items lifetime is calculated, considering the date it was created until the date it was closed. Therefore, only closed items are considered in this metric. It is also necessary to inform the desired timeframe used to calculate the items lifetime.
The following example shows the Pulls lifetime average for all closed pulls within last 15 days:
```shell
./github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a calc-repo-pulls-lifetime -d 15
```
The same for Issues:
```shell
./github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a calc-repo-issues-lifetime -d 15
```

### Events
List the repository events from the last 24 hours:
```shell
github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a list-repo-events
```

### Labels
List the repository labels and their respective colors and descriptions:
```shell
github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a list-repo-labels
```