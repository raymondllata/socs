import argparse
import socket
import time

from ocs import ocs_agent, site_config
from ocs.ocs_twisted import TimeoutLock

from socs.agents.scpi_psu.ethernet_drivers import \
    PsuInterface as PsuEthernetInterface
from socs.agents.scpi_psu.gpib_drivers import PsuInterface as PsuGpibInterface


class ScpiPsuAgent:
    def __init__(self, agent, ip_address, gpib_slot):
        self.agent = agent
        self.log = agent.log
        self.lock = TimeoutLock()

        self.job = None
        self.ip_address = ip_address
        self.gpib_slot = gpib_slot
        self.monitor = False

        self.psu = None

        # Registers Temperature and Voltage feeds
        agg_params = {
            'frame_length': 10 * 60,
        }
        self.agent.register_feed('psu_output',
                                 record=True,
                                 agg_params=agg_params,
                                 buffer_time=0)

    @ocs_agent.param('_')
    def init(self, session, params=None):
        """init()

        **Task** - Initialize connection to the power supply.

        """
        with self.lock.acquire_timeout(0) as acquired:
            if not acquired:
                return False, "Could not acquire lock"

            if self.gpib_slot is not None:
                print("Connecting to PSU via GPIB/Ethernet Connection")
                self.gpib_slot = int(self.gpib_slot)
                try:
                    self.psu = PsuGpibInterface(self.ip_address, self.gpib_slot)
                except socket.timeout as e:
                    self.log.error("PSU timed out during connect")
                    return False, "Timeout"
            else:
                try:
                    print("Connecting to PSU via Ethernet Connection")
                    self.psu = PsuEthernetInterface(self.ip_address)
                except socket.timeout as e:
                    self.log.error("PSU timed out during connect")
                    return False, "Timeout"

            self.idn = self.psu.identify()
            self.log.info("Connected to psu: {}".format(self.idn))

        return True, 'Initialized PSU.'

    @ocs_agent.param('wait', type=float, default=1)
    @ocs_agent.param('channels', type=list, default=[1, 2, 3])
    @ocs_agent.param('test_mode', type=bool, default=False)
    def monitor_output(self, session, params=None):
        """monitor_output(wait=1, channels=[1, 2, 3], test_mode=False)

        **Process** - Continuously monitor PSU output current and voltage.

        Parameters:
            wait (float, optional): Time to wait between measurements
                [seconds].
            channels (list[int], optional): Channels to monitor. [1, 2, 3] by
                default.
            test_mode (bool, optional): Exit process after single loop if True.
                Defaults to False.

        """
        session.set_status('running')
        self.monitor = True

        while self.monitor:
            with self.lock.acquire_timeout(1) as acquired:
                if acquired:
                    data = {
                        'timestamp': time.time(),
                        'block_name': 'output',
                        'data': {}
                    }

                    for chan in params['channels']:
                        data['data']["Voltage_{}".format(chan)] = self.psu.get_volt(chan)
                        data['data']["Current_{}".format(chan)] = self.psu.get_curr(chan)

                    # self.log.info(str(data))
                    # print(data)
                    self.agent.publish_to_feed('psu_output', data)

                    # Allow this process to be queried to return current data
                    session.data = data

                else:
                    self.log.warn("Could not acquire in monitor_current")

            time.sleep(params['wait'])

            if params['test_mode']:
                break

        return True, "Finished monitoring current"

    def stop_monitoring(self, session, params=None):
        self.monitor = False
        return True, "Stopping current monitor"

    @ocs_agent.param('channel', type=int, choices=[1, 2, 3])
    @ocs_agent.param('volts', type=float, check=lambda x: 0 <= x <= 30)
    def set_voltage(self, session, params=None):
        """set_voltage(channel, volts)

        **Task** - Set the voltage of the power supply.

        Parameters:
            channel (int): Channel number (1, 2, or 3).
            volts (float): Voltage to set. Must be between 0 and 30.

        """

        with self.lock.acquire_timeout(1) as acquired:
            if acquired:
                self.psu.set_volt(params['channel'], params['volts'])
            else:
                return False, "Could not acquire lock"

        return True, 'Set channel {} voltage to {}'.format(params['channel'], params['volts'])

    @ocs_agent.param('channel', type=int, choices=[1, 2, 3])
    @ocs_agent.param('current', type=float)
    def set_current(self, session, params=None):
        """set_current(channel, current)

        **Task** - Set the current of the power supply.

        Parameters:
            channel (int): Channel number (1, 2, or 3).
            current (float): Current to set.

        """
        with self.lock.acquire_timeout(1) as acquired:
            if acquired:
                self.psu.set_curr(params['channel'], params['current'])
            else:
                return False, "Could not acquire lock"

        return True, 'Set channel {} current to {}'.format(params['channel'], params['current'])

    @ocs_agent.param('channel', type=int, choices=[1, 2, 3])
    @ocs_agent.param('state', type=bool)
    def set_output(self, session, params=None):
        """set_output(channel, state)

        **Task** - Turn a channel on or off.

        Parameters:
            channel (int): Channel number (1, 2, or 3).
            state (bool): True for on, False for off.

        """
        with self.lock.acquire_timeout(1) as acquired:
            if acquired:
                self.psu.set_output(params['channel'], params['state'])
            else:
                return False, "Could not acquire lock"

        return True, 'Initialized PSU.'


def make_parser(parser=None):
    """Build the argument parser for the Agent. Allows sphinx to automatically
    build documentation based on this function.

    """
    if parser is None:
        parser = argparse.ArgumentParser()

    # Add options specific to this agent.
    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--ip-address')
    pgroup.add_argument('--gpib-slot')

    return parser


def main(args=None):
    parser = make_parser()
    args = site_config.parse_args(agent_class='ScpiPsuAgent',
                                  parser=parser,
                                  args=args)

    agent, runner = ocs_agent.init_site_agent(args)
    print("Connecting to IP: " + args.ip_address)
    if args.gpib_slot is None:
        print("Connecting to PSU via Ethernet-only Interface")
    else:
        print("Connecting to GPIB: " + args.gpib_slot)
        print("Connecting to PSU via GPIB/Ethernet Interface")

    # Test IP Formatting
    try:
        socket.inet_aton(args.ip_address)
        # legal
    except socket.error:
        # Not legal
        print("Invalid IP Format")

    p = ScpiPsuAgent(agent, args.ip_address, args.gpib_slot)

    agent.register_task('init', p.init)
    agent.register_task('set_voltage', p.set_voltage)
    agent.register_task('set_current', p.set_current)
    agent.register_task('set_output', p.set_output)

    agent.register_process('monitor_output', p.monitor_output, p.stop_monitoring)

    runner.run(agent, auto_reconnect=True)


if __name__ == '__main__':
    main()
