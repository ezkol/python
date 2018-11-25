import requests
import json
from subprocess import call
import os
import time
import datetime
import filecmp
import  re
from requests.auth import HTTPBasicAuth

# git clone https://github.com/globocom/m3u8.git
# python3.6 setup.py install
import m3u8

class DirCmp:
	def __init__(self,src,dst):
		self.src = src;
		self.dst = dst;
	def cmp(self):

		d1_contents = set(os.listdir(self.src))
		d2_contents = set(os.listdir(self.dst))
		#common = list(d1_contents & d2_contents)
		common = list(d1_contents)
		common_files = [
		    f
		    for f in common
		    if os.path.isfile(os.path.join(self.src, f))
		]
		print('Common files:', common_files)

		# Compare the directories
		match, mismatch, errors = filecmp.cmpfiles(
		    self.src,
		    self.dst,
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
		out = "../out/" + out
		print("out path " + out)
		res = requests.get(self.url + "/video/" + file, allow_redirects=True)
		open(out, 'wb').write(res.content)
		self.segs.append(res.headers['Via'])

	def get_playlist_segs(self,playlist,num_segs):
		segs = []
		res =  requests.get(url = self.url + playlist)
		m3u8_obj = m3u8.loads(res.text)
		#m3u8_obj.dumps().splitlines()
		seg_list = [key.uri for key in m3u8_obj.segments]
		[self.download(x) for x in seg_list[:num_segs]]
		return self.segs #res.status_code == 200

class TrafficVault:
	pswd = str(os.environ['VAULT_PASS'])
	usr  = str(os.environ['VAULT_USER'])
	session = requests.Session()
	session.verify = False
	session.auth = (usr , pswd)

	def __init__(self,url):
		self.base = url
	def login(self):
		return self.session.get(self.base + '/ping').status_code == 200
		print(res.status_code)
		print(res.text)
class TrafficOps:
	session = requests.Session()
	session.verify = False

	pswd = str(os.environ['OPS_PASS'])
	usr  = str(os.environ['OPS_USER'])

	data = {"u" : usr , "p" : pswd}
	headers = {"Content-Type" : "application/x-www-form-urlencode" }

	def __init__(self,url):
		self.base = url
		self.url_login   = self.base + "/api/1.2/user/login"
		self.url_servers = self.base + "/api/1.2/servers.json"
		self.url_status =  self.base + "/server/updatestatus"
		self.url_crconfig= self.base + "/tools/write_crconfig/cdn"
	
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

	def __init__(self,url):
		self.base = url
		self.url_states = self.base + "/publish/CrStates"

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


class ViaParser:
	codes = {}
	codes[1] = {}
	codes[1]['title'] = "client-info Request headers received from client. Value is one of:"
	codes[1]['I'] = "If Modified Since (IMS)"
	codes[1]['C'] = "cookie"
	codes[1]['E'] = "error in request"
	codes[1]['S'] = "simple request (not conditional)"
	codes[1]['N'] = "no-cache"
	codes[2] = {}
	codes[2]['title'] = "cache-lookup Result of Traffic Server cache lookup for URL. Value is one of:"
	codes[2]['A'] = "in cache, not acceptable (a cache \"MISS\")"
	codes[2]['H'] = "in cache, fresh (a cache \"HIT\")"
	codes[2]['S'] = "in cache, stale (a cache \"MISS\")"
	codes[2]['R'] = "in cache, fresh Ram hit (a cache \"HIT\")"
	codes[2]['M'] = "miss (a cache \"MISS\")"
	codes[2][' '] = "no cache lookup performed"
	codes[3] = {}
	codes[3]['title'] = "server-info Response information received from origin server. Value is one of:"
	codes[3]['E'] = "error in response"
	codes[3][' '] = "no server connection needed"
	codes[3]['S'] = "served"
	codes[3]['N'] = "not-modified"
	codes[4] = {}
	codes[4]['title'] = "cache-fill Result of document write to cache. Value is one of:"
	codes[4]['U'] = "updated old cache copy"
	codes[4]['D'] = "cached copy deleted"
	codes[4]['W'] = "written into cache (new copy)"
	codes[4][' '] = "no cache write performed"
	codes[5] = {}
	codes[5]['title'] = "proxy-info Proxy operation result. Value is one of:"
	codes[5]['R'] = "origin server revalidated"
	codes[5][' '] = "unknown?"
	codes[5]['S'] = "served"
	codes[5]['N'] = "not-modified"
	codes[6] = {}
	codes[6]['title'] = "error-codes Value is one of:"
	codes[6]['A'] = "authorization failure"
	codes[6]['H'] = "header syntax unacceptable"
	codes[6]['C'] = "connection to server failed"
	codes[6]['T'] = "connection timed out"
	codes[6]['S'] = "server related error"
	codes[6]['D'] = "dns failure"
	codes[6]['N'] = "no error"
	codes[6]['F'] = "request forbidden"
	codes[7] = {}
	codes[7]['title'] = "tunnel-info Proxy-only service operation. Value is one of:"
	codes[7][' '] = "no tunneling"
	codes[7]['U'] = "tunneling because of url (url suggests dynamic content)"
	codes[7]['M'] = "tunneling due to a method (e.g. CONNECT)"
	codes[7]['O'] = "tunneling because cache is turned off"
	codes[7]['F'] = "tunneling due to a header field (such as presence of If-Range header)"
	codes[8] = {}
	codes[8]['title'] = "cache-type and cache-lookup cache result values (2 characters)"
	codes[8]['I'] = "icp"
	codes[8][' '] = "cache miss or no cache lookup"
	codes[8]['C'] = "cache"
	codes[9] = {}
	codes[9]['title'] = "cache-lookup-result character value is one of:"
	codes[9][' '] = "no cache lookup"
	codes[9]['S'] = "cache hit, but expired"
	codes[9]['U'] = "cache hit, but client forces revalidate (e.g. Pragma: no-cache)"
	codes[9]['D'] = "cache hit, but method forces revalidated (e.g. ftp, not anonymous)"
	codes[9]['I'] = "conditional miss (client sent conditional, fresh in cache, returned 412)"
	codes[9]['H'] = "cache hit"
	codes[9]['M'] = "cache miss (url not in cache)"
	codes[9]['C'] = "cache hit, but config forces revalidate"
	codes[9]['N'] = "conditional hit (client sent conditional, doc fresh in cache, returned 304)"
	codes[10] = {}
	codes[10]['title'] = "icp-conn-info ICP status"
	codes[10][' '] = "no icp"
	codes[10]['S'] = "connection opened successfully"
	codes[10]['F'] = "connection open failed"
	codes[11] = {}
	codes[11]['title'] = "parent-proxy parent proxy connection status"
	codes[11][' '] = "no parent proxy"
	codes[11]['S'] = "connection opened successfully"
	codes[11]['F'] = "connection open failed"
	codes[12] = {}
	codes[12]['title'] = "server-conn-info origin server connection status"
	codes[12][' '] = "no server connection"
	codes[12]['S'] = "connection opened successfully"
	codes[12]['F'] = "connection open failed"
	
	def parse(self,via):
		name = via.split()[1]
		sub = via[via.find("[")+1:via.find("]")].split(":")
		### WARNING one of the blank values is missing - length should be 24 not less ###
		if (not sum( len(x) for x in sub) >= 23) : return
		#print("Traffic Server cache lookup for URL : " + self.codes[2][sub[0][3]])
		#print("Cache-type and cache-lookup cache result values : " + self.codes[9][sub[1][4]])
		#print("Response information received from origin server : " + self.codes[3][sub[0][5]])
		#print("Document write-to-cache : " + self.codes[4][sub[0][7]])
		#print("Error codes : " + self.codes[6][sub[0][11]])
		print(name + ":" + self.codes[2][sub[0][3]] + "," + self.codes[9][sub[1][4]] + "," +  self.codes[3][sub[0][5]] + "," + self.codes[4][sub[0][7]] + "," + self.codes[6][sub[0][11]])
if(0):
	#hls = Hls("https://bitdash-a.akamaihd.net/content/sintel/hls/")
	hls = Hls("http://tr." + str(os.environ['SERVICE_NAME']) + "." + str(os.environ['DOMAIN']) + "/assets/sintel/") # master.m3u8
	vias = hls.get_playlist_segs("/video/250kbit.m3u8",10)
	print(vias)
	vp = ViaParser()
	res = [vp.parse(x) for x in vias]
		
	exit()
	cm = DirCmp('../out' , '../ref')
	cm.cmp()


#exit()

ts = "c23-atsec-01"
tm = TrafficMonitor("http://c23-tm-01")
tv = TrafficVault("https://c23-tv-01")
to = TrafficOps("https://c23-to-01")

if not (tv.login()): exit()
if not (tm.are_all_caches_avail()):  exit() 
if not (to.login()): exit()

print("check admin down")
to.set_admin_status(ts , "ADMIN_DOWN")
if (tm.wait_cache_avail(ts , False)): exit()

print("check reported")
to.set_admin_status(ts , "REPORTED")
if  (tm.wait_cache_avail(ts , True)): exit()
print("TEST FINISHED OK")
