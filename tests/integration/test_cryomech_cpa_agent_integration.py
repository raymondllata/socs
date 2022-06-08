import os
import pytest

import ocs
from ocs.base import OpCode

from ocs.testing import (
    create_agent_runner_fixture,
    create_client_fixture,
)

from integration.util import (
    create_crossbar_fixture
)

from socs.testing.device_emulator import create_device_emulator

pytest_plugins = ("docker_compose")

# Set the OCS_CONFIG_DIR so we read the local default.yaml file always
os.environ['OCS_CONFIG_DIR'] = os.getcwd()

# Raw bytes message/response for Agent init
init_msg = b'\t\x99\x00\x00\x00\x06\x01\x04\x00\x01\x005'
init_res = b'\t\x99\x00\x00\x00m\x01\x04j\x00\x00\x00\x00\x00\x00\x80\x00\x00\x00\x80\x00A\x06B\x83\xfcjB\x82k\x85B\x84\xe6fB\x85.\xb8C[\t\x0cC[\xf1\x82CZ6\xeeC[\xd8\x00\xbetwG>`\xd6\x00F%\x00\x00\x00\x00)<\x04\x18\x02\x9a\x04u\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

wait_for_crossbar = create_crossbar_fixture()
run_agent = create_agent_runner_fixture(
    '../agents/cryomech_cpa/cryomech_cpa_agent.py', 'cryomech_cpa_agent')
client = create_client_fixture('cryomech')
emulator = create_device_emulator({init_msg: init_res}, relay_type='tcp', port=5502, encoding=None)


@pytest.mark.integtest
def test_cryomech_cpa_init(wait_for_crossbar, emulator, run_agent,
                           client):
    resp = client.init.wait()
    resp = client.init.status()
    print(resp)
    assert resp.status == ocs.OK
    print(resp.session)
    assert resp.session['op_code'] == OpCode.SUCCEEDED.value


# @pytest.mark.integtest
# def test_pfeiffer_tc400_turn_turbo_on(wait_for_crossbar, emulator, run_agent,
#                                      client):
#    client.init()
#
#    responses = {'0011001006111111015': format_reply('111111'),  # ready_turbo()
#                 '0011002306111111019': format_reply('111111'),  # turn_turbo_motor_on()
#                 }
#    emulator.define_responses(responses)
#
#    resp = client.turn_turbo_on()
#    print(resp)
#    assert resp.status == ocs.OK
#    print(resp.session)
#    assert resp.session['op_code'] == OpCode.SUCCEEDED.value
