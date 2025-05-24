import argparse
import datetime
import json
import socket
import sys
import time
import asyncio
import goodwe
import influxdb


def do_every(period: int,f,*args) -> None:
    """
    Execute function f periodically with period period seconds.
    If execution of f exceeds period then next is executed without delay until back on schedule.
    """
    def g_tick():
        """
        Generate time to next scheduled tick with period period
        """
        t = time.time()
        while True:
            t += period
            yield max(t - time.time(), 0)
    g = g_tick()
    while True:
        time.sleep(next(g))
        f(*args)


class Goodwe2Influx:
    """
    Read GoodWe sensor and settings parameters and store in InfluxDB 1.x database.
    """
    def __init__(self, inverterhostaddress: str, invertermacaddress: str, interval: int, influxhost: str,
                 influxport: int, influxusername: str, influxpassword: str, influxdatabase: str,
                 influxmeasurement: str, inverterid: str, mappings: dict, verbose: bool, dryrun: bool
    ):
        self._inverterhostaddress = inverterhostaddress
        self._invertermacaddress = invertermacaddress
        self._interval = interval
        self._influxhost = influxhost
        self._influxport = influxport
        self._influxusername = influxusername
        self._influxpassword = influxpassword
        self._influxdatabase = influxdatabase
        self._influxmeasurement = influxmeasurement
        self._inverterid = inverterid
        self._mappings = mappings
        self._verbose = verbose
        self._dryrun = dryrun
        self._inverterlastreachable = datetime.datetime.min
        self._inverter = None


    def run(self) -> None:
        """
        Read from inverter and store in database in loop.
        """
        while not self._scanconnect():
            print(f"No IP address known. Retry in {self._interval}s.", file=sys.stderr)
            time.sleep(5)
        do_every(self._interval, self._run)


    def _run(self) -> None:
        """
        Read from inverter and store in database.
        """
        try:
            inverterdata = self._get_inverter_data()
            point = self._format_influxpoint(inverterdata)
            self._write_influx(point)
        except goodwe.RequestFailedException as e:
            if self._verbose:
                print(f"RequestFailedException: {self._inverterhostaddress}: {e}", file=sys.stdout)
        except goodwe.InverterError as e:
            if self._verbose:
                print(f"InverterError: {self._inverterhostaddress}: {e}", file=sys.stdout)

    def _get_inverter_data(self) -> dict:
        """
        Get sensor and settings data from Goodwe inverter.
        Precondition: self._inverterhostaddress != None
        :return: sensor and setting data
        :raises: RequestFailedException, InverterError
        """
        async def get_inverter_data_async(inverter) -> dict:
            sensor_data = await inverter.read_runtime_data()
            settings_data = await inverter.read_settings_data()
            return sensor_data | settings_data

        self._scanconnect()
        inverterdata = asyncio.run(get_inverter_data_async(self._inverter))
        self._update_inverter_last_reacheable()
        return inverterdata


    def _connect(self, reconnect: bool = False) -> None:
        """
        Connect to inverter
        """
        async def connect_async(host: str) -> goodwe.Inverter:
            timeout = 5
            return await goodwe.connect(host, timeout=timeout, retries=self._interval // timeout)

        try:
            if (not self._inverter or reconnect) and self._inverterhostaddress:
                self._inverter = asyncio.run(connect_async(self._inverterhostaddress))
                self._update_inverter_last_reacheable()
        except goodwe.InverterError as e:
            pass


    def _scanconnect(self) -> bool:
        """
        Update IP address for inverter MAC address. (Re)connect to scanner.
        :returns: True if at least connected once to inverter, False otherwise
        """
        self._connect()
        if not self._invertermacaddress:
            return self._inverter is not None  # macadress is prerequisite for scan
        if datetime.datetime.now() - self._inverterlastreachable < datetime.timedelta(minutes = 15):
            return self._inverter is not None  # only scan when not reachable for more than 15 minutes

        if self._verbose:
            print(f"Scanning for inverters.", file=sys.stdout)
        inverters = Goodwe2Influx.scan()
        for inverter in inverters:
            if not inverter['mac'] == self._invertermacaddress:
                continue
            ipchange = not self._inverterhostaddress == inverter['ip']
            if ipchange:
                print(f"Update inverter IP to {inverter['ip']}", file=sys.stdout)
            self._inverterhostaddress = inverter['ip']
            self._update_inverter_last_reacheable()
            self._connect(reconnect = ipchange)
            return self._inverter is not None
        return self._inverter is not None


    def _update_inverter_last_reacheable(self) -> None:
        """
        Update last time inverter IP was reachable.
        """
        self._inverterlastreachable = datetime.datetime.now()


    def _format_influxpoint(self, inverterdata: dict) -> dict:
        """
        Prepare Influx point from inverterdata using mappings.
        """
        fields = {self._mappings[mapping]: inverterdata.get(mapping) for mapping in self._mappings}
        point = {
            "measurement": self._influxmeasurement,
            "tags": {
                "inverter": self._inverterid
            },
            "fields": fields
        }
        return point


    def _write_influx(self, point: dict) -> None:
        """
        Write Goodwe sensor and settings data to Influx database. Supports Influx 1.x.
        """
        if not self._dryrun:
            influxdbclient = influxdb.InfluxDBClient(self._influxhost, self._influxport,
                                                     self._influxusername, self._influxpassword,
                                                     self._influxdatabase)
            influxdbclient.write_points([point])
        if self._verbose:
            print(f"InfluxDB point: {point}", file=sys.stdout)


    @staticmethod
    def scan() -> list[dict]:
        """
        Scans network for Goodwe inverter. Replaces non-functional goodwe.search_inverters().
        :return: list of inverters, dict per inverter with keys 'ip', 'mac' and 'name'
        """
        broadcast_ip_address = '255.255.255.255'
        goodwe_port = 48899
        goodwe_hello = "WIFIKIT-214028-READ"
        inverters = []
        attributes = ['ip', 'mac', 'name']

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.2)
        sock.sendto(goodwe_hello.encode('utf-8'), (broadcast_ip_address, goodwe_port))
        while True:
            try:
                data, _ = sock.recvfrom(1024)
                fields = data.decode("utf-8").split(",")
                inverters.append({attribute: fields[i] for i, attribute in enumerate(attributes)})
            except TimeoutError:
                break
        sock.close()
        return inverters


def load_mappings(mappingfile: str) -> dict:
    """
    Load inverter-database field mapping from json file.
    """
    with open(mappingfile, 'r') as fin:
        mappings = json.loads(fin.read())
        if not isinstance(mappings, dict):
            raise TypeError("mapping file format error")
    return mappings


def print_inverters(inverters: list[dict]) -> None:
    """
    Print inverters information.
    """
    if not inverters:
        print(f'No inverters found.')
        return
    for i, inverter in enumerate(inverters):
        print(f"Inverter #{i}   IP-address: {inverter['ip']}   "
              f"MAC-address: {inverter['mac']}   name: {inverter['name']}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='Goodwe2Influx',
        description='Read Goodwe sensor and settings parameters and store in InfluxDB 1.x database.')
    parser.add_argument('--invertermac', default=None,
                        help='MAC address of Inverter.\n'
                             '--invertermac (recommended) or --inverterhost must be specified.\n'
                             'Leave both empty to scan for inverters with their MAC and IP addresses.')
    parser.add_argument('--inverterhost', default=None,
                        help='IP address, hostname or FQDN of Inverter.\n'
                             'IP only recommended with static IP adresses.\n'
                             'In combination with --invertermac only used for initial connection.')
    parser.add_argument('--interval', default=30, type=int,
                        help='Time period in seconds between inverter readings. Default: 30s.')
    parser.add_argument('--influxhost', default='localhost',
                        help='Hostname or IP address of InfluxDB server. Default: localhost.')
    parser.add_argument('--influxport', default=8086,
                        help='Network port number of InfluxDB server. Default: 8086.')
    parser.add_argument('--influxusername', default='',
                        help='InfluxDB username. Default: (empty).')
    parser.add_argument('--influxpassword', default='',
                        help='InfluxDB password. Default: (empty).')
    parser.add_argument('--influxdatabase', default='defaultdb',
                        help='InfluxDB database name (pre-created). Default: defaultdb.')
    parser.add_argument('--influxmeasurement', default='goodwe',
                        help='Influx measurement (table) name to store inverter data. Default: goodwe.')
    parser.add_argument('--inverterid', default='goodwe1',
                        help='Inverver identifier to identify inverter in database. Default: goodwe1.')
    parser.add_argument('--mappingfile', default='mapping-default.json',
                        help='Path to file with inverter-database field mapping. Default: mapping-default.json.')
    parser.add_argument('-v', '--verbose',
                        action='store_true', help='Print startup configuration and data readings to stdout.')
    parser.add_argument('--dryrun',
                        action='store_true', help='Do not make database changes.')
    return parser.parse_args()


def main():
    args = parse_arguments()
    mappings = load_mappings(args.mappingfile)

    if args.verbose or (not args.invertermac and not args.inverterhost):
        print_inverters(Goodwe2Influx.scan())
    if not args.invertermac and not args.inverterhost:
        exit(0)

    if args.verbose:
        configjsonstr = json.dumps(vars(args)|{'mappings': mappings}, indent=4)
        print(f'\nConfiguration from commandline and mapping file: {configjsonstr}')

    gi = Goodwe2Influx(args.inverterhost, args.invertermac, args.interval, args.influxhost, args.influxport,
                       args.influxusername, args.influxpassword, args.influxdatabase,
                       args.influxmeasurement, args.inverterid, mappings, args.verbose, args.dryrun)
    gi.run()


if __name__ == "__main__":
    main()

