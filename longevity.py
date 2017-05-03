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

SCALE = 1000
N_THREADS = 10

def run_cmd(msg, cmd):
  p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  out, err = p.communicate()
  print "%s: [%s] %s => %d(%s)" % (datetime.datetime.now(), msg, cmd, p.returncode, repr(out))
  return p.returncode

def fatal_error(msg):
  print msg
  # Just kill the test so we can debug
  run_cmd("", "killall python")

def load_containers_now(thread, containers):
  ps_out = subprocess.check_output("rancher ps -c --format json", shell=True)
  ps_out_list = map(json.loads, ps_out.splitlines())
  containers.clear()
  for c in ps_out_list:
    if u'primaryIpAddress' in c[u'Container']:
      ip = c[u'Container'][u'primaryIpAddress'].encode('ascii','replace')
      st = c[u'Container'][u'state'].encode('ascii','replace')
      if st == 'running':
        ct = c[u'Container'][u'created'].encode('ascii','replace')
        # We only test containers that have been created 120 seconds ago because it takes time for networking to get established
        if (datetime.datetime.now() - datetime.datetime.strptime(ct, "%Y-%m-%dT%H:%M:%SZ")).total_seconds() > 120:
          containers[c[u'ID'].encode('ascii','replace')] = ip
  print "%s: thread = %s %d containers=" % (datetime.datetime.now(), thread, len(containers)) + str(containers)

def net_test(thread, containers):
  iteration = 0
  while True:
    keys = containers.keys()
    if len(keys) >= 1:
      source = keys[int(len(keys) * random.random())]
      source_ip = containers.get(source)
      target = keys[int(len(keys) * random.random())]
      target_ip = containers.get(target)
      # Another thread could have cleared these keys
      if source_ip != None and target_ip != None:
        cmd = "rancher exec %s curl -sSf http://%s -o /dev/null" % (source, target_ip)
        code = run_cmd("%s, %d" % (thread, iteration) , cmd)
        if code != 0:
          fatal_error("ERROR when running %s" % (cmd))
      iteration = iteration + 1
    time.sleep(6) # 10 tests a minute

def load_containers(containers):
  while True:
    load_containers_now("load_containers", containers)
    time.sleep(30)

run_cmd("", "rancher rm `rancher ps -q`")
run_cmd("", "rancher run shengliang/apache-php --scale %d" % (SCALE))

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

for p in workers:
  p.join()
