# CommunityMon
This project was created with the goal of collecting metrics from relevant tools and representing them in nice dashboards, which can ultimately provide insights for maintainers and quickly accessible data to support Open Source project management.

![Grafana Dashboard](Screenshot_Grafana.png)

# Architecture
The project is composed by a stack of containers, which work together to collect metrics, store data in a time series database and finally represent them in dashboards.

The stack is configured in a `docker-compose.yaml` file, which is processed by the [podman-compose](https://github.com/containers/podman-compose) tool.

## Containers
### prometheus
[prometheus](https://prometheus.io/) is the core solution chosen for this project. It is a robust and, at the same time, a light tool used to collect many useful metrics and store them in time series database, which can be easily consumed by [grafana](https://grafana.com/oss/grafana/).

prometheus is a tool which was initially designed to collect metrics from web applications. However, it permits creation of custom metrics, which makes it capable to monitor almost everything.

All the prometheus configuration is centralized in the `prometheus.yml` file. Examine this file is the prometheus documentation for more details.

### pushgateway
[pushgateway](https://github.com/prometheus/pushgateway) is under the prometheus umbrella and was created to act as a proxy between prometheus and the monitored asset which doesn't natively provide metrics in the format required by prometheus.

Using pushgateway is also a straightforward option for send ing custom metrics to prometheus time series database. In the context of this project, where the volume of data is not large and the metrics are collected by scripts, pushgateway fits very well.

### grafana
[grafana](https://grafana.com/oss/grafana/) is a very popular and useful solution to create nice dashboards. This solution converted the boring task of traditionally creating dynamic charts and dashboards in a easy and intuitive task. Useful dashboards can be created with the minimal effort and time.

## API Scripts
Currently, the project has scripts which interact with the Github Rest API to collect some metrics and send to `pushgateway`.

Any contribution to include support for more APIs or even improve what is already in place is always more than welcome!! ; )

## Workflow
Basically, `scripts` interact with the tools' APIs to collect relevant data and send them to `pushgateway`. Then `prometheus` consults the `pushgateway` to get aware of the custom metrics and store them on its time series database. Finally, `grafana` can access the `prometheus` data and use the available metrics on its dashboards.

# Get Started
It is pretty straightforward to start using this stack. You only need to follow some few steps to start monitoring your Open Source project.
## Requirements
### Python Modules
> pip install PyGithub prometheus_client

### Packages
#### Fedora
> dnf install -y podman-compose

### Content
> git clone https://github.com/marcusburghardt/CommunityMon.git

### Tokens
#### Github
Read the respective documentation to generate your token:
* https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token

Once the token is generated, create a file in a place you consider secure, with the following content:
```dotnetcli
[DEFAULT]
github_token = ghp_*****
```
Inform the absolute path for this file in the `api.conf` file.

## Start
Navigate to the folder where the `docker-compose.yaml` file is located and execute the following command:
> podman-compose up -d

### Access the tools
* Grafana: [locahost:3000](http://localhost:3000)
* Prometheus: [locahost:9090](http://localhost:9090)
* Pushgateway: [locahost:9091](http://localhost:9091)

### Collect the first metrics
The following example is collecting metrics from the Github `ComplianceAsCode` organization and the `ComplianceAsCode/content` repository, considering issues and pulls which are without updates longer than `15` days as old issues and pulls. Finally, the script action is to `push-metrics` to prometheus:
> ./CommunityMon/APIs/github_monitor.py -o ComplianceAsCode -r ComplianceAsCode/content -a push-metrics-prometheus -d 15

Check the `Metrics.md` file in `Docs` folder for more information about the collected metrics.

### Explore the scripts
The scripts can also be used to collect data for ad-hoc analysis. Check the `Examples.md` file in `Docs` folder for inspiration. ;)
