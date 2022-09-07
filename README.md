
# Contextual Cybernation

ADARCA (API Driven Automated Root Cause Analysis) focuses on gathering, aggregating, correlation, and analyzing ecolgoical context. After analyzing the context, it assigns a root cause probability, uses this to make decisions, and automate appropriate actions.

## Table of Contents
* [Getting Started](#getting-started)
    * [Locally](#locally)
        * [Requirements](#requirements)
        * [Installation](#installation)
        * [Usage](#usage)
    * [Docker](#docker)
        * [Requirements](#requirements-1)
        * [Installation](#installation-1)
        * [Usage](#usage-1)
* [TODO](#todo)
* [Authors](#authors)
* [History](#history)
* [License](#license)

## Getting Started

The following instructions assume you have the following environment:

Observability Tool: [PRTG](https://www.paessler.com/prtg)

* Notifcation trigger with Execute HTTP (to PRTG integration in Opsgenie)

Alerting Tool: [Opsgenie](https://www.atlassian.com/software/opsgenie)

* PRTG integration setup
* REST API integration
* Action Channel and Action Rest HTTP to ADARCA

ITSM: [ServiceNow](https://www.servicenow.com/)

### Locally

This is to get ADARCA up and running without Docker. Without a reverse proxy (or some other way for the Alerting Tool to communicate with ADARCA), this isn't very useful. There are some options, like Opsgenie's [OEC](https://support.atlassian.com/opsgenie/docs/opsgenie-edge-connector-as-an-extensibility-platform/) which provides a way to execute scripts behind a firewall. 

#### Requirements

* Python
    * _Note: Developed using Python 3.9.5, but was not tested with any other version._

#### Installation

1. Download code from GitHub

    ```bash
    git clone https://github.com/CC-Digital-Innovation/Contextual-Cybernation.git
    ```

    * or download the zip: https://github.com/CC-Digital-Innovation/Contextual-Cybernation/archive/refs/heads/main.zip

2. Create virtual environment

    ```bash
    python3 -m venv example-env
    ```

3. Activate virtual environment

    ```bash
    source example-env/bin/activate
    ```

    On Windows:
    ```powershell
    example-env\Scripts\Activate.ps1
    ```

4. Download required packages

    ```bash
    pip install -r requirements.txt
    ```

#### Usage

* Open or copy the configuration file `config.yaml.exmaple`. Make adjustments to the file as necessary and rename to `config.yaml`.
* For the purposes of a demo, a simulated API was used. Switch the `SimulatedSupportApi`:
    ```python
    from cisco.support import SupportApi
    # from cisco.support import SimulatedSupportApi
    ...
    # SIM_CISCO_SUPPORT_API = SimulatedSupportApi()
    SIM_CISCO_SUPPORT_API = SupportApi(client_id, client_secret)
    ```

* Start ADARCA:
   ``` bash
   python3 main.py
    ```

### Docker

#### Requirements

* Docker
    *  _Note: Developed using version 20.10.8_
* docker-compose
    * _Note: Developed using version 1.29.2_

#### Installation

1. Download code from GitHub

    ```bash
    git clone https://github.com/CC-Digital-Innovation/Contextual-Cybernation.git
    ```

    * or download the zip: https://github.com/CC-Digital-Innovation/Contextual-Cybernation/archive/refs/heads/main.zip

#### Usage

* Open or copy the configuration file `config.yaml.exmaple`. Make adjustments to the file as necessary and rename to `config.yaml`.
* For the purposes of a demo, a simulated API was used. Switch the `SimulatedSupportApi`:
    ```python
    from cisco.support import SupportApi
    # from cisco.support import SimulatedSupportApi
    ...
    # SIM_CISCO_SUPPORT_API = SimulatedSupportApi()
    SIM_CISCO_SUPPORT_API = SupportApi(client_id, client_secret)
    ```
* This compose file takes advantage of [Caddy as a reverse proxy](https://github.com/lucaslorentz/caddy-docker-proxy). Follow the basic usage to setup the network and container.
*   Edit the hostname (if setup) inside `docker-compose.yml`
    ```bash
    ...
    labels:
      caddy: power-api.quokka.ninja
    ...
    ```
* Run ADARCA
    ```bash
    docker-compose up -d --build
    ```

## TODO

* Change geocoding API to [Nominatim](https://nominatim.org/release-docs/develop/api/Overview/)
* Move to Kubernetes cluster
* Support other APIs for data collection

## Authors
* Jonny Le <<jonny.le@computacenter.com>>

## History

See [CHANGELOG.md](https://github.com/CC-Digital-Innovation/PowerOutageMonitor/blob/main/CHANGELOG.md)

## License
MIT License

Copyright (c) 2021 Computacenter Digital Innovation

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
