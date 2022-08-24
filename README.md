
# Contextual Cybernation

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/) 

These python scripts use a series of API requests to check if a given address (USA) has an ongoing power outage or not. The data is parsed from a CSV or a JSON file. The script currently uses two open REST APIs, PGE and GIS to check for outage status. 

## Table of Contents
* [Getting Started](#getting-started)
    * [Requirements](#requirements)
    * [Installation](#installation)
    * [Usage](#usage)
* [Authors](#authors)
* [History](#history)
* [License](#license)

## Getting Started

### Requirements

* Python
    * _Note: Developed using Python 3.8.7 64-bit, but was not tested with any other version._

### Installation

1. Download code from GitHub

    ```bash
    git clone https://github.com/CC-Digital-Innovation/PowerOutageMonitor.git
    ```

    * or download the zip: https://github.com/CC-Digital-Innovation/PowerOutageMonitor/archive/refs/heads/main.zip

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
    example-env\Scripts\activate.bat
    ```
4. Install required modules

    ```bash
    pip install -r requirements.txt
    ```

### Usage

* The configuration file ([config.yaml](https://github.com/CC-Digital-Innovation/PowerOutageMonitor/blob/main/config.yaml)) can run as is. Make adjustments to the file as necessary.
* The data files, site.csv and site.json must be changed to have real address and names for real-world application.
* For customization, only need to edit the check_site.py file main() function. The default implementation shows different API calls and data parsing methods.
* To run the script on a terminal to make appropriate changes, navigate to the directory and run the following command: -  
   ``` bash
   python3 check_site.py
    ```

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
