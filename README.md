# GoodWe2Influx

Python 3 script to read GoodWe sensor and settings parameters and store in InfluxDB 1.x database.  

## Install

### Satisfy pre-requisites:
- Python 3
- optionally: virtual environment
- InfluxDB 1.x database

### Download goodwe2influx
```commandline
git clone https://github.com/pkoster/goodwe2influx.git
```

### Install dependencies
```commandline
pip install -r requirements.txt
```
GoodWe2Influx needs the following modules:
- goodwe  
  GoodWe inverter client.
- influxdb  
  Influx 1.x client.
- asyncio  
  Asynchronous IO for goodwe module.

### Configure mappings  
Mappings define the sensor and settings to be stored. 
Use ```mapping-default.json``` as-is or make a copy and adapt it to your needs.
```json
{
 "vpv1": "vpv1_V",
 "vpv2": "vpv2_V",
 "ipv1": "ipv1_A",
 ...
}
```
Each row adds a field with a sensor or setting value to the database. 

The lefthandside string identifies the sensor or setting name of the GoodWe inverter. 
The meaning of most names can be found in the
[Python GoodWe library](https://github.com/marcelblijleven/goodwe/blob/58c7f8e4b0b95ce6c3ff2fbd61b4c32a6c3665c2/goodwe/dt.py).

The righthandside string specifies the fieldname in the Influx database.

## Run
### Commandline arguments
```commandline
$ python goodwe2influx.py -h
usage: Goodwe2Influx [-h] [--invertermac INVERTERMAC] [--inverterhost INVERTERHOST] [--interval INTERVAL] [--influxhost INFLUXHOST]
                     [--influxport INFLUXPORT] [--influxusername INFLUXUSERNAME] [--influxpassword INFLUXPASSWORD]
                     [--influxdatabase INFLUXDATABASE] [--influxmeasurement INFLUXMEASUREMENT] [--inverterid INVERTERID]
                     [--mappingfile MAPPINGFILE] [-v] [--dryrun]

Read Goodwe sensor and settings parameters and store in InfluxDB 1.x database.

options:
  -h, --help            show this help message and exit
  --invertermac INVERTERMAC
                        MAC address of Inverter. --invertermac (recommended) or --inverterhost must be specified. Leave both empty to scan
                        for inverters with their MAC and IP addresses.
  --inverterhost INVERTERHOST
                        IP address, hostname or FQDN of Inverter. IP only recommended with static IP adresses. In combination with
                        --invertermac only used for initial connection.
  --interval INTERVAL   Time period in seconds between inverter readings. Default: 30s.
  --influxhost INFLUXHOST
                        Hostname or IP address of InfluxDB server. Default: localhost.
  --influxport INFLUXPORT
                        Network port number of InfluxDB server. Default: 8086.
  --influxusername INFLUXUSERNAME
                        InfluxDB username. Default: (empty).
  --influxpassword INFLUXPASSWORD
                        InfluxDB password. Default: (empty).
  --influxdatabase INFLUXDATABASE
                        InfluxDB database name (pre-created). Default: defaultdb.
  --influxmeasurement INFLUXMEASUREMENT
                        Influx measurement (table) name to store inverter data. Default: goodwe.
  --inverterid INVERTERID
                        Inverver identifier to identify inverter in database. Default: goodwe1.
  --mappingfile MAPPINGFILE
                        Path to file with inverter-database field mapping. Default: mapping-default.json.
  -v, --verbose         Print startup configuration and data readings to stdout.
  --dryrun              Do not make database changes.
```
### Scan inverters
```commandline
$ python goodwe2influx.py
Inverter #0   IP-address: 192.168.1.89   MAC-address: 289C6E64xxxx   name: Solar-WiFi228Rxxxx
```
Copy the MAC-address.
### Test reading inverter
The ```-v``` argument prints more output.
The ```--dryrun``` argument avoids database changes.
```commandline
$ python goodwe2influx.py --invertermac 289C6E64xxxx --dryrun -v                      
Inverter #0   IP-address: 192.168.1.89   MAC-address: 289C6E64278E   name: Solar-WiFi228R0056                                               
Configuration from commandline and mapping file: {
    "invertermac": "289C6E64xxxx",
    "inverterhost": null,
    "interval": 30,
    "influxhost": "localhost",
    "influxport": 8086,
    "influxusername": "",
    "influxpassword": "",
    "influxdatabase": "defaultdb",
    "influxmeasurement": "goodwe",
    "inverterid": "goodwe1",
    "mappingfile": "mapping-default.json",
    "verbose": true,
    "dryrun": true,
    "mappings": {
        "vpv1": "vpv1_V",
        "vpv2": "vpv2_V",
        "ipv1": "ipv1_A",
        "ipv2": "ipv2_A",
        "ppv1": "ppv1_W",                                                                                                                           "ppv2": "ppv2_W",                                                                                                                           "ppv": "ppv_W",                                                                                                                             "vline1": "vline1_V",                                                                                                                       "vline2": "vline2_V",                                                                                                                       "vline3": "vline3_V",                                                                                                                       "vgrid1": "vgrid1_V",
        "vgrid2": "vgrid2_V",
        "vgrid3": "vgrid3_V",                                                                                                                       "igrid1": "igrid1_A",
        "igrid2": "igrid2_A",                                                                                                                       "igrid3": "igrid3_A",
        "fgrid1": "fgrid1_Hz",                                                                                                                      "fgrid2": "fgrid2_Hz",
        "fgrid3": "fgrid3_Hz",
        "pgrid1": "pgrid1_W",
        "pgrid2": "pgrid2_W",
        "pgrid3": "pgrid3_W",
        "total_inverter_power": "total_inverter_power_W",
        "work_mode": "work_mode",
        "error_codes": "error_codes",
        "warning_code": "warning_code",
        "apparent_power": "apparent_power_W",
        "reactive_power": "reactive_power_W",
        "power_factor": "power_factor",
        "temperature": "temperature_C",
        "e_day": "e_day_kWh",
        "e_total": "e_total_kWh",
        "h_total": "h_total_h",
        "safety_country": "safety_country",
        "derating_mode": "derating_mode",
        "grid_export": "grid_export",
        "grid_export_limit": "grid_export_limit_pct",
        "start": "start",
        "stop": "stop",
        "restart": "restart",
        "grid_export_hw": "grid_export_hw"
    }
}
Scanning for inverters.
Update inverter IP to 192.168.1.89
InfluxDB point: {'measurement': 'goodwe', 'tags': {'inverter': 'goodwe1'}, 'fields': {'vpv1_V': 366.6, 'vpv2_V': 383.0, 'ipv1_A': 0.4, 'ipv2_A': 0.4, 'ppv1_W': 147, 'ppv2_W': 153, 'ppv_W': 300, 'vline1_V': 393.5, 'vline2_V': 392.7, 'vline3_V': 390.7, 'vgrid1_V': 227.0, 'vgrid2_V': 227.1, 'vgrid3_V': 225.5, 'igrid1_A': 0.7, 'igrid2_A': 0.7, 'igrid3_A': 0.7, 'fgrid1_Hz': 49.99, 'fgrid2_Hz': 49.98, 'fgrid3_Hz': 49.98, 'pgrid1_W': 159, 'pgrid2_W': 159, 'pgrid3_W': 158, 'total_inverter_power_W': 236, 'work_mode': 1, 'error_codes': 0, 'warning_code': 0, 'apparent_power_W': 0, 'reactive_power_W': -124, 'power_factor': 0.901, 'temperature_C': 44.6, 'e_day_kWh': 46.9, 'e_total_kWh': 21424.7, 'h_total_h': 10549, 'safety_country': 32, 'derating_mode': 4, 'grid_export': 0, 'grid_export_limit_pct': 200, 'start': 0, 'stop': 0, 'restart': 0, 'grid_export_hw': 0}}
```
### Run
Specify commandline arguments for Influx and other.
```commandline
$ python goodwe2influx.py --invertermac 289C6E64xxxx
```
## Acknowledgements
Goodwe2influx relies on the Python [goodwe module](https://github.com/marcelblijleven/goodwe).   
[solar2influx](https://github.com/jaccolo/solar2influx) served as inspiration.