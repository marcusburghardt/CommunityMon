# Metrics
Here are described the metrics currently collected and sent to prometheus.

## Organizations
* <org_id>_org_admins: Count of admins on <org_id>
* <org_id>_org_members: Count of members on <org_id>
* <org_id>_org_repositories: Count of repositories on <org_id>
* <org_id>_org_team_size: Count of team members as specified in `apis.yml` file

## Repositories
* <org_id>_<repo_id>_archived: Is archived? False or True
* <org_id>_<repo_id>_closed_issues_30days: Number of closed issues within last 30 days.
* <org_id>_<repo_id>_closed_issues_30days_team: Number of closed team issues within last 30 days. Team issues means issues reported by team members, as defined in `apis.yml` file.
* <org_id>_<repo_id>_closed_issues_90days: Number of closed issues within last 90 days.
* <org_id>_<repo_id>_closed_issues_90days_team: Number of closed team issues within last 90 days. Team issues means issues reported by team members, as defined in `apis.yml` file.
* <org_id>_<repo_id>_closed_pulls_30days: Number of closed pulls within last 30 days.
* <org_id>_<repo_id>_closed_pulls_30days_team: Number of closed team pulls within last 30 days. Team pulls means pulls reported by team members, as defined in `apis.yml` file.
* <org_id>_<repo_id>_closed_pulls_90days: Number of closed pulls within last 90 days.
* <org_id>_<repo_id>_closed_pulls_90days_team: Number of closed team pulls within last 90 days. Team pulls means pulls reported by team members, as defined in `apis.yml` file.
* <org_id>_<repo_id>_contributors: Number of contributors.
* <org_id>_<repo_id>_created_issues_30days: Number of created issues within last 30 days.
* <org_id>_<repo_id>_created_issues_30days_team: Number of created team issues within last 30 days. Team issues means issues reported by team members, as defined in `apis.yml` file.
* <org_id>_<repo_id>_created_issues_90days: Number of created issues within last 90 days.
* <org_id>_<repo_id>_created_issues_90days_team: Number of created team issues within last 90 days. Team issues means issues reported by team members, as defined in `apis.yml` file.
* <org_id>_<repo_id>_created_pulls_30days: Number of created pulls within last 30 days.
* <org_id>_<repo_id>_created_pulls_30days_team: Number of created team pulls within last 30 days. Team pulls means pulls reported by team members, as defined in `apis.yml` file.
* <org_id>_<repo_id>_created_pulls_90days: Number of created pulls within last 90 days.
* <org_id>_<repo_id>_created_pulls_90days_team: Number of created team pulls within last 90 days. Team pulls means pulls reported by team members, as defined in `apis.yml` file.
* <org_id>_<repo_id>_events: Number of events from the last 24 hours.
* <org_id>_<repo_id>_forks_count: Number of forks.
* <org_id>_<repo_id>_issues_lifetime_average_30days: Average lifetime of closed issues within last 30 days.
* <org_id>_<repo_id>_issues_lifetime_average_30days_team: Average lifetime of closed team issues within last 30 days. Team issues means issues reported by team members, as defined in `apis.yml` file.
* <org_id>_<repo_id>_issues_lifetime_average_90days: Average lifetime of closed issues within last 90 days.
* <org_id>_<repo_id>_issues_lifetime_average_90days_team: Average lifetime of closed team issues within last 90 days. Team issues means issues reported by team members, as defined in `apis.yml` file.
* <org_id>_<repo_id>_labels_count: Number of existing labels in the repository.
* <org_id>_<repo_id>_old_open_issues: Number of issues without updates within n days.
* <org_id>_<repo_id>_old_open_pulls: Number of pulls without updates within n days.
* <org_id>_<repo_id>_open_issues: Number of open issues. This metric comes from repository issues query.
* <org_id>_<repo_id>_open_issues_count: Number of open issues, including pulls, which are also considered issues for Github. This metric comes from the repository info and not by issues query.
* <org_id>_<repo_id>_open_issues_<label>: Number of open issues filtered by label. There is an equivalent metric for each label defined in the `apis.yml` file. In the `apis.yml` file the label should be written as it is. However, the metric id canonize the label name in order to respect the Prometheus requirements.
* <org_id>_<repo_id>_open_pulls: Number of open PRs.
* <org_id>_<repo_id>_private: Is private? False or True
* <org_id>_<repo_id>_pulls_lifetime_average_30days: Average lifetime of closed pulls within last 30 days.
* <org_id>_<repo_id>_pulls_lifetime_average_30days_team: Average lifetime of closed team pulls within last 30 days. Team pulls means pulls reported by team members, as defined in `apis.yml` file.
* <org_id>_<repo_id>_pulls_lifetime_average_90days: Average lifetime of closed pulls within last 90 days.
* <org_id>_<repo_id>_pulls_lifetime_average_90days_team: Average lifetime of closed team pulls within last 90 days. Team pulls means pulls reported by team members, as defined in `apis.yml` file.
* <org_id>_<repo_id>_stargazers_count: Number of stars for the repository.
* <org_id>_<repo_id>_subscribers_count: Number of subscribers (watchers)
* <org_id>_<repo_id>_unassigned_open_issues: Number of open issues without an assignee.
* <org_id>_<repo_id>_unassigned_open_pulls: Number of open pulls without an assignee.
