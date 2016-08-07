#!/usr/bin/env python
"""This module uses Ansible to deploy device configurations and provide diffs
across many vendors.
"""

DOCUMENTATION = '''
---
module: netmiko_install_config
author: Tyler Christiansen
version_added: "0.0.1"
short_description: Load configuration onto a device running IOS-like software.
description:
    - Load a snippets of Cisco IOS-style configuration.  Despite the misleading
      name, this module is compatible with many different vendors.  Although
      it is compatible with Juniper, it is strongly recommended that you use
      Juniper's ansible-junos-stdlib modules.
      You provide the configuration data in a file.  The configuration can be
      a complete configuration or snippets.  The file is iterated through and
      executed in order of the lines.  Because IOS and IOS-like devices do
      not have syntax validation prior to configuration, this module cannot
      guarantee a file you supply is valid for that device.
requirements:
    - netmiko >= 0.1.3
options:
    host:
        description:
            - Set to {{ inventory_hostname }}
        required: true
    user:
        description:
            - Login username
        required: false
        default: $USER
    passwd:
        description:
            - Login password
        required: false
        default: key-based authentication
    file:
        description:
            - Path to the file containing the configuration data.
        required: true
    device_type:
        description:
            - OS type.  See the NetMiko documentation for details.
        required: false
        default: cisco_ios
    log_file:
        description:
            - Path on the local server where the output is logged for
              debugging purposes
        required: false
        default: None
    diff_file:
        description:
            - Path to the file where any diffs will be written
        required: false
        default: None
'''

EXAMPLES = '''
# load a cisco-style configuration file
- netmiko_install_config:
    host={{ inventory_hostname }}
    file=ospf.conf
# specify a user
- netmiko_install_config:
    host={{ inventory_hostname }}
    file=bgp.conf
    user=unicorn
# log output and diff file
- netmiko_install_config:
    host={{ inventory_hostname }}
    file=vstp.conf
    log_file=output.log
    diff_file=config.diff
# specify a different device type
- netmiko_install_config:
    host={{ inventory_hostname }}
    file=ldp.conf
    device_type=brocade_vdx
'''

import logging
import os
import difflib
import sys

try:
    import netmiko
    MEETS_REQUIREMENTS = True
except ImportError as e:
    MEETS_REQUIREMENTS = False

def get_config(dev):
    """Returns the current configuration of an IOS-like device that supports
    `show running-config`
    """
    return dev.send_command("show running-config")

def install_config(module, dev):
    """Installs a complete or partial configuration on an IOS-like device by
    sending commands one at a time to the remote device.
    """
    args = module.params
    results = {}
    config_file = os.path.abspath(args['file'])
    results['file'] = config_file
    results['changed'] = False

    logging.info("loading %s", config_file)

    try:
        if not dev.check_enable_mode():
            dev.enable()
        # NetMiko automatically enters config mode, but not enable mode
        dev.send_config_from_file(config_file=config_file)
        results['changed'] = True
    except Exception as err:
        logging.error("Exception: %s", err.message)
        raise err

    dev.exit_config_mode()
    return results

def diff_config(cfg_old, cfg_new):
    """performs a diff on `cfg_old` and `cfg_new`, returning the resulting
    diff.
    """
    return difflib.unified_diff(cfg_old.strip().splitlines(),
                                cfg_new.strip().splitlines(),
                                fromfile='old config',
                                tofile='new config',
                                lineterm='')

def load(module):
    """Kicks off the process of installing a configuration on an IOS-like device
    and determining if that device's previous and new configurations should be
    diffed.
    """
    args = module.params
    logfile = args['log_file']

    if logfile is not None:
        logging.basicConfig(filename=logfile, level=logging.INFO,
                            format='%(asctime)s:%(name)s:%(message)s')
        logging.getLogger().name = 'CONFIG:' + args['host']

    logging.info("connecting to %s", args['host'])
    dev_params = {"device_type": args['device_type'],
                  "ip": args['host'],
                  "username": args['user'],
                  "password": args['passwd'],
                  "verbose": False}

    try:
        dispatcher = netmiko.ssh_dispatcher(device_type=args['device_type'])
        dev = dispatcher(**dev_params)
    except Exception as err:
        logging.error("Exception: %s", err.message)
        raise err

    if args['diff_file']:
        original_config = get_config(dev)

    results = install_config(module, dev)
    if args['diff_file']:
        new_config = get_config(dev)
        diff = diff_config(original_config, new_config)
        if diff is not None:
            diff_file = module.params['diff_file']
            if diff_file is not None:
                try:
                    with open(diff_file, "w") as file_handle:
                        file_handle.write('\n'.join(diff))
                except Exception as err:
                    logging.error("Exception: %s", err.message)
                    raise err

    module.exit_json(**results)


def main():
    """Kicks off the Ansible bootstrapping.
    """
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(required=True),
            user=dict(required=False, default=os.getenv('USER')),
            passwd=dict(required=False, default=None),
            file=dict(required=True),
            device_type=dict(required=False, default='cisco_ios'),
            log_file=dict(required=False, default=None),
            diff_file=dict(required=False, default=None)
        ),
        supports_check_mode=False)

    if not MEETS_REQUIREMENTS:
        logging.error(sys.path)
        print(sys.path)
        module.fail_json(msg='netmiko >= 0.1.3 is required for this module {}'.format(e))
        return

    load(module)

from ansible.module_utils.basic import *
main()
