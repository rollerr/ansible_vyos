#!/home/workplace/src/bin/python2.7

from netmiko import ConnectHandler
import sys

working_dir = '/home/workplace/src/ansible/vyos/output/'
file_name = sys.argv[1]

vyos = {'device_type': 'vyos', 'ip': '192.168.2.241', 'username':'vyos', 'password':'vyos'}
import pdb;pdb.set_trace()
print('hi')

conn = ConnectHandler(**vyos)

conn.send_config_from_file(working_dir+file_name)