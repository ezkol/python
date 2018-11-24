import requests
import json
from subprocess import call
import os

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

	def admin_down(self, name):
		server = list(filter(lambda x: x["hostName"] == name , self.session.get(url = self.url_servers).json()["response"]))[0]
		print(server["id"])
		data = "id=" + str(server["id"]) + "&status=REPORTED"
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

		res = self.session.get(url = self.url_crconfig)
		print(res)
#curl -c /tmp/cookies.txt -v -s -k -X POST --data '{ "u":"'"$TRAFFIC_OPS_USER"'", "p":"'"$TRAFFIC_OPS_PASS"'" }' $TRAFFIC_OPS_URI/api/1.2/user/login
#curl -b /tmp/cookies.txt -v -k -H "Content-Type: application/x-www-form-urlencoded" -X POST $ADDITONAL_DATA --data-urlencode "id=$TMP_SERVER_ID" --data-urlencode "status=$STATUS" $TRAFFIC_OPS_URI/server/updatestatus
#write CR Config
# curl -b /tmp/cookies.txt -k --header "X-XSRF-TOKEN: $TMP_TO_COOKIE" $TRAFFIC_OPS_URI/tools/write_crconfig/$CDN_NAME

class TrafficMonitor:

	url_states = "http://localhost/publish/CrStates"

	def are_all_caches_avail(self):
		data = requests.get(url = self.url_states).json()
		print(data["caches"])
		#num_caches = len(data["caches"].items())
		#for key , value  in data["caches"].items():
		#	print(key, value["isAvailable"])
		#[ expression for item in list if conditional ]
		return len(data["caches"].items()) == sum([ 0 if value["isAvailable"] == "True" else 1 for key , value in data["caches"].items()])
		#print(list)

	def is_cache_avail(self,cache):
		data = requests.get(url = self.url_states).json()
		print(data["caches"])
		return 1 == len([ 0 if value["isAvailable"] == "True" else 1 for key , value in data["caches"].items() if key == cache])

	def description(self):
		desc_str = "name %s url_state %s" % (self.name, self.url_states)
		return desc_str
		
	def __init__(self, name):
		self.name = name
if (1):
	tm = TrafficMonitor("TrafficMonitor")
	if (tm.are_all_caches_avail()):
		print("all caches are available")
	if (tm.is_cache_avail("k8s-node-02")):
		print("k8s-node-02 available")
	else:	
		print("k8s-node-03 is not available")

to = TrafficOps()
if (to.login()):
	print("login ok")
to.admin_down("k8s-node-02")

