import requests
import json
from subprocess import call
import os
import time

class TrafficOps:
	session = requests.Session()
	session.verify = False

	url_login = "https://10.0.40.150/api/1.2/user/login"
	url_servers = "https://10.0.40.150/api/1.2/servers.json"
	url_status = "https://10.0.40.150/server/updatestatus"
	url_crconfig = "https://10.0.40.150/tools/write_crconfig/cdn"
	pswd = str(os.environ['OPS_PASS'])
	usr = str(os.environ['OPS_USER'])
	data = {"u" : usr , "p" : pswd}
	headers = {"Content-Type" : "application/x-www-form-urlencode" }
	def login(self):
		call([
    			'curl',
			'-H',
			json.dumps(self.headers), #'Content-Type: application/x-www-form-urlencoded',
    			'-X',
    			'POST',
			'-k',
			'-c',
			'/tmp/cookies.txt',
    			'--data',
    			json.dumps(self.data),
    			self.url_login
		])

		return self.session.post(url = self.url_login , data = json.dumps(self.data) , headers = self.headers).status_code == 200

	def set_admin_status(self, name,status):
		server = list(filter(lambda x: x["hostName"] == name , self.session.get(url = self.url_servers).json()["response"]))[0]
		print(server["id"])
		data = "id=" + str(server["id"]) + "&status=" + status
		call([
    			'curl',
			'-H',
			json.dumps(self.headers), #'Content-Type: application/x-www-form-urlencoded',
    			'-X',
    			'POST',
			'-k',
			'-b',
			'/tmp/cookies.txt',
    			'--data',
    			data, #'id=7&status=REPORTED',#json.dumps(admin_stat),
    			self.url_status
		])

		return self.session.get(url = self.url_crconfig).status_code == 200

class TrafficMonitor:

	url_states = "http://localhost/publish/CrStates"

	def are_all_caches_avail(self):
		data = requests.get(url = self.url_states).json()
		print(data["caches"])
		#[ expression for item in list if conditional ]
		return len(data["caches"].items()) == sum([ 0 if value["isAvailable"] == "True" else 1 for key , value in data["caches"].items()])
		#print(list)

	def is_cache_avail(self,name):
		data = requests.get(url = self.url_states).json()
		print(data["caches"])
		return 1 == sum([ 1 if value["isAvailable"] == True else 0 for key , value in data["caches"].items() if key == name])

	def wait_cache_avail(self,name):
		sec = 0
		while sec < 100 and not self.is_cache_avail(name): 
			sec += 5
			time.sleep(5)
		return self.is_cache_avail(name)

	def __init__(self, name):
		self.name = name
#if (1):
tm = TrafficMonitor("TrafficMonitor")
#if (tm.are_all_caches_avail()):
#	print("all caches are available")
#if (tm.is_cache_avail("k8s-node-02")):
#	print("k8s-node-02 available")
#else:	
#	print("k8s-node-03 is not available")

to = TrafficOps()
if (to.login()):
	print("login ok")
else:
	printt("error login in")

to.set_admin_status("k8s-node-02","REPORTED")
#to.set_admin_status("k8s-node-02","ADMIN_DOWN")
#time.sleep(20)
tm.wait_cache_avail("k8s-node-02")

