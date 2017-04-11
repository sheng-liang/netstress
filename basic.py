import subprocess
import time
import random
import sys
import threading
import time
import os
import mmap
import json
from os import path
import stat
import datetime

from multiprocessing import Process, Manager, Array, current_process, Lock

SCALE = 200
N_THREADS = 10

def fatal_error(msg):
  print msg
  # Just kill the test so we can debug
  subprocess.call("killall python", shell = True)

def load_containers_now(thread, containers):
  ps_out = subprocess.check_output("rancher ps -c --format json", shell=True)
  ps_out_list = map(json.loads, ps_out.splitlines())
  containers.clear()
  for c in ps_out_list:
    if u'primaryIpAddress' in c[u'Container']:
      ip = c[u'Container'][u'primaryIpAddress']
      st = c[u'Container'][u'state']
      if st == 'running':
        containers[c[u'ID'].encode('ascii','replace')] = ip.encode('ascii','replace')
  print "%s: thread = %s containers=" % (datetime.datetime.now(), thread) + str(containers)

def net_test(thread, containers):
  iteration = 0
  while True:
    keys = containers.keys()
    if len(keys) >= 1:
      source = keys[int(len(keys) * random.random())]
      target = keys[int(len(keys) * random.random())]
      print "%s: thread = %s iteration = %d %s(%s) => %s(%s)" % (datetime.datetime.now(), thread, iteration, source, containers[source], target, containers[target])
      cmd = "rancher exec %s curl -sSf http://%s -o /dev/null" % (source, containers[target])
      p = subprocess.Popen(cmd, shell=True)
      p.communicate()
      if p.returncode != 0:
        # Make sure containers are still around so we did not get the error because source or target was killed.
        time.sleep(20) # Sleep for 20 seconds because Rancher takes time to reflect container state
        load_containers_now(thread, containers)
        updated_keys = containers.keys()
        if source in updated_keys and target in updated_keys:
          fatal_error("ERROR when running %s" % (cmd))
      iteration = iteration + 1
    else:
      time.sleep(1)

def load_containers(containers):
  while True:
    load_containers_now("load_containers", containers)
    time.sleep(5)

def kill_containers(containers):
  while True:
    keys = containers.keys()
    if len(keys) >= 1:
      target = keys[int(len(keys) * random.random())]
      subprocess.call("rancher rm %s" % (target), shell = True)
    time.sleep(10)

def kill_hosts():
  while True:
    host_out = subprocess.check_output("rancher host --format json", shell=True)
    host_out_list = map(json.loads, host_out.splitlines())
    l = len(host_out_list)
    if l > 1:
      host = host_out_list[int(l * random.random())][u'ID'].encode('ascii','replace')
      subprocess.call("rancher stop %s" % host, shell = True)
      time.sleep(60)
      subprocess.call("rancher rm %s" % host, shell = True)
      p = subprocess.Popen("./add-host.sh", shell = True)
      p.communicate()
      if p.returncode != 0:
        fatal_error("ERROR adding host")
    time.sleep(600)


subprocess.call("rancher rm `rancher ps -q`", shell = True)
subprocess.call("rancher run shengliang/apache-php --scale %d" % (SCALE), shell = True)

workers = []

manager = Manager()

containers = manager.dict()

for thread in xrange(N_THREADS):
  p = Process(target = net_test, args = (str(thread + 1), containers))
  workers.append(p)
  p.start()

p = Process(target = load_containers, args = (containers,))
workers.append(p)
p.start()

p = Process(target = kill_containers, args = (containers,))
workers.append(p)
p.start()

p = Process(target = kill_hosts, args = ())
workers.append(p)
p.start()


for p in workers:
  p.join()
