import requests
import json
from subprocess import call
import os
import time
import datetime
import filecmp

# git clone https://github.com/globocom/m3u8.git
# python3.6 setup.py install
import m3u8
# Determine the items that exist in both directories

class DirCmp:
	def cmp(self):

		d1_contents = set(os.listdir('../out'))
		d2_contents = set(os.listdir('../ref'))
		common = list(d1_contents & d2_contents)
		common_files = [
		    f
		    for f in common
		    if os.path.isfile(os.path.join('../out', f))
		]
		print('Common files:', common_files)

		# Compare the directories
		match, mismatch, errors = filecmp.cmpfiles(
		    '../out',
		    '../ref',
		    common_files,
		)
		print('Match       :', match)
		print('Mismatch    :', mismatch)
		print('Errors      :', errors)
		return mismatch + errors == 0

class Hls:
	def __init__(self,url):
		self.url = url; #  + "/video/250kbit.m3u8"

	segs = []
	def download(self,file):
		print("download " + self.url + "/video/" + file)
		out =  file.rsplit('/', 1)[1]
		out = "../ref/" + out
		print("out path " + out)
		res = requests.get(self.url + "/video/" + file, allow_redirects=True)
		open(out, 'wb').write(res.content)
		#print(int(res.headers['Access-Control-Max-Age']) == 86400)
		print('86400' in res.headers['Access-Control-Max-Age'])
		self.segs.append(res.headers['Access-Control-Max-Age'])

	def get_playlist_segs(self,playlist,num_segs):
		segs = []
		res =  requests.get(url = self.url + playlist)
		m3u8_obj = m3u8.loads(res.text)
		#m3u8_obj.dumps().splitlines()
		seg_list = [key.uri for key in m3u8_obj.segments]
		[self.download(x) for x in seg_list[:num_segs]]
		return self.segs #res.status_code == 200

class TrafficVault:
	def login(self):
		pswd = str(os.environ['OPS_PASS'])
		usr  = str(os.environ['RIAK'])
		res = call([
    			'curl',
			'-k',
			'-s',
    			'--user',
    			usr + ':' + pswd,
    			'https://traffic-vault/ping'	
		])
		print(res)
		return res == 0
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

	def wait_cache_avail(self,name,avail):
		sec = 0
		while sec < 100 and not self.is_cache_avail(name) == avail: 
			sec += 5
			print(datetime.datetime.now())
			time.sleep(5)
		return self.is_cache_avail(name)

#hls = Hls("https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8")
hls = Hls("https://bitdash-a.akamaihd.net/content/sintel/hls/")
segs = hls.get_playlist_segs("/video/250kbit.m3u8",5)
print(segs)
exit()
cm = DirCmp()
cm.cmp()
exit()

#if (1):
tm = TrafficMonitor()
#if (tm.are_all_caches_avail()):
#	print("all caches are available")
#if (tm.is_cache_avail("k8s-node-02")):
#	print("k8s-node-02 available")
#else:	
#	print("k8s-node-03 is not available")

tv = TrafficVault()
tv.login()

to = TrafficOps()
if (to.login()):
	print("login ok")
else:
	printt("error login in")

to.set_admin_status("k8s-node-02","ADMIN_DOWN")
tm.wait_cache_avail("k8s-node-02",False)
to.set_admin_status("k8s-node-02","REPORTED")
tm.wait_cache_avail("k8s-node-02",True)
