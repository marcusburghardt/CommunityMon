# Metrics
Here are described the metrics currently collected and sent to prometheus.

## Organizations
* <org_id>_org_admins: Count of admins on <org_id>
* <org_id>_org_members: Count of members on <org_id>
* <org_id>_org_repositories: Count of repositories on <org_id>

## Repositories
* <repo_id>_forks_count: Number of forks.
* <repo_id>_stargazers_count: Number of stars for the repository.
* <repo_id>_subscribers_count: Number of subscribers (watchers)
* <repo_id>_archived: Is archived? False or True
* <repo_id>_private: Is private? False or True
* <repo_id>_contributors: Number of contributors.
* <repo_id>_events: Number of events from the last 24 hours.
* <repo_id>_open_issues_count: Number of open issues.
* <repo_id>_open_pulls: Number of open PRs.
* <repo_id>_old_open_issues: Number of issues without updates within n days. 
* <repo_id>_old_open_pulls: Number of pulls without updates within n days.
* <repo_id>_pulls_lifetime_average: Average lifetime of closed pulls from last 90 days.
* <repo_id>_closed_pulls_90days: Number of closed pulls from last 90 days.
* <repo_id>_created_pulls_90days: Number of created pulls from last 90 days.
* <repo_id>_open_issues_label_label\_\<label\>: Number of open issues on <repo_id> with label \<label\>.
