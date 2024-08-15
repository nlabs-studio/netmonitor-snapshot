import argparse
import ipaddress
import keyboard
import pickle
import psutil
import requests
import socket
import time
import os
from datetime import datetime

# the number of days before a requery is necessary to update cache entries
g_requery_in_days = 3

# global quit flag for kb termination
g_quit_flag = False

# the default refresh interval between cycles (using seconds)
g_refresh_interval = 10

# network utilities
class NetworkUtils:
    @staticmethod
    def get_geolocation(ip, token = '', is_commerial = True):
        headers = {'User-Agent': 'NLabs.Studio Netmonitor Snapshot'}
        try:            
            api_url = f"https://ipinfo.io/{ip}/json"
            if len(token) > 0:
                api_url = f"https://ipinfo.io/{ip}/json?token={token}"
            response = requests.get(api_url, headers=headers)
            data = response.json()
            if is_commerial:
                return None

            # fall back option if rate limit has been exceeded 
            # the end-user has specified a non-commercial use case 
            # exists
            if 'error' in data:
                api_url = f"http://ip-api.com/json/{ip}?fields=country,regionName,city,lat,lon,isp,query"
                response = requests.get(api_url, headers=headers)
                data = response.json()
                if 'lat' in data:
                    data['loc'] = data['lat']+','+data['lon']
                    data['ip'] = data['query']
                    data['region'] = data['regionName']
                    data['hostname'] = data['isp']
            return data
        except:
            return None
    @staticmethod
    def is_internal(ip):
        try:
            ip_obj = ipaddress.ip_address(ip)
            if isinstance(ip_obj, ipaddress.IPv4Address):
                return ip_obj.is_private
            elif isinstance(ip_obj, ipaddress.IPv6Address):
                if ip_obj.is_link_local or ip_obj.is_private:
                    return True
                return False
        except:
            return False
    @staticmethod
    def reverse_dns(ip):
        try:
            hn, _, _ = socket.gethostbyaddr(ip)
            return hn
        except socket.herror:
            return None

# network ip address information
class IP_AddressInfo:
    def __init__(self, ip_addr, hostname, city, region, country, location):
        self._ip_addr = ip_addr
        self._hostname = hostname
        self._city = city
        self._region = region
        self._country = country
        self._location = location
        self._log_time = time.time()
    def __str__(self):
        return self._ip_addr +','+ self._hostname +',' + self._city + ','+ self._region + ',' + self._country +',' + self._location
    def ipAddress(self):
        return self._ip_addr
    def hostname(self):
        return self._hostname
    def city(self):
        return self._city
    def region(self):
        return self._region
    def country(self):
        return self._country
    def location(self):
        return self._location
    def logTime(self):
        return self._log_time

# report writer
class ReportWriter:
    # cl - dictionary of SocketConnection objects
    # il - dictionary of IP_AddressInfo objects
    # mr - (optional) produce multiple document reports
    @staticmethod
    def write(cl, il, mr = False):

        date_t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filepath_t = 'nlabs.studio_report.htm' if not mr else date_t.replace(':', '_').replace('-', '_') + '_nlabs.studio_report.htm'

        f = open(filepath_t, 'w', encoding='utf-8')
        f.write("<html>")
        f.write("<head>")

        if not mr:
            f.write('<meta http-equiv="refresh" content="'+str(g_refresh_interval)+'; url=nlabs.studio_report.htm">')

        f.write("<title>NLabs.Studio Netmonitor Snapshot Report</title>")
        f.write('<style type="text/css">')
        f.write("body{margin:0;padding:20px 0px 0px 20px;background-color:#000000;color:#ffffff;font-size:13px;}")
        f.write("h1{font-size:20px;padding:0;margin:0;color:#ffffff;}")
        f.write(".pl{padding-left:20px;}")
        f.write("p{font-size:20px;margin:0px;padding:0px;}")
        f.write("th{cursor:pointer;}")
        f.write(".mt{margin-top:10px;}")
        f.write("</style>")
        f.write('<script type="text/javascript">')
        f.write("var gcv = function(tr, idx){ return tr.children[idx].innerText || tr.children[idx].textContent; };var c = function(idx, asc) { return function(a, b) { return function(v1, v2) {return v1 !== '' && v2 !== '' && !isNaN(v1) && !isNaN(v2) ? v1 - v2 : v1.toString().localeCompare(v2);}(gcv(asc ? a : b, idx), gcv(asc ? b : a, idx));}};window.onload = function(){Array.prototype.slice.call(document.querySelectorAll('th')).forEach(function(th) { th.addEventListener('click', function() {var table = th.parentNode;while(table.tagName.toUpperCase() != 'TABLE') table = table.parentNode;Array.prototype.slice.call(table.querySelectorAll('tr:nth-child(n+2)')).sort(c(Array.prototype.slice.call(th.parentNode.children).indexOf(th), this.asc = !this.asc)).forEach(function(tr) { table.appendChild(tr) });})});};")
        f.write("</script>")
        f.write("</head>")
        f.write("<body>")
        f.write('<table id="data_table">')
        f.write('<tr valign="top" cellspacing="10">')
        f.write('<td><a href="https://www.nlabs.studio" target="_blank"><img src="data:image/png;base64,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" alt="" /></a></td>')
        f.write('<td class="pl"><h1>NLabs.Studio Snapshot Report</h1><p class="mt">Autonomous network monitoring reports for TCP/UDP connections active on the (NIC) network interface card.</p></td>')
        f.write("</tr>")
        f.write("</table>")
        f.write("<br />")
        f.write("<p>Report produced at "+ date_t +" with "+ str(len(cl)) +" connections and "+ str(len(il)) +" entries in cache</p>")
        f.write('<table cellspacing="10">')
        f.write("<tr>")
        f.write('<th align="left">Local</th>')
        f.write('<th align="left">Remote</th>')
        f.write('<th align="left">Type</th>')
        f.write('<th align="left">Time</th>')
        f.write('<th align="left">State</th>')        
        f.write('<th align="left">City</th>')
        f.write('<th align="left">Region</th>')
        f.write('<th align="left">Country</th>')
        f.write('<th align="left">Long &amp; Lat</th>')
        f.write('<th align="left">Hostname</th>')        
        f.write("</tr>")

        for key, c in cl.items():

            i = il[key]

            f.write("<tr>")
            f.write('<td><span style="color:#F5428A;">'+ c.localIP() +"</span>:"+ str(c.localPort()) +"</td>")
            f.write('<td><span style="color:#F5428A;">'+ c.remoteIP() +"</span>:"+ str(c.remotePort()) +"</td>")

            ctype = 'TCP/IP'
            if str(c.connectionType()) == 'SocketKind.SOCK_DGRAM':
                ctype = 'UDP/IP'
            f.write("<td>"+ ctype +"</td>")

            dt = datetime.fromtimestamp(c.time())
            f.write("<td>"+ dt.strftime('%Y-%m-%d %H:%M:%S') +"</td>")

            f.write("<td>"+ c.status() +"</td>")            
            f.write("<td>"+ i.city() +"</td>")
            f.write("<td>"+ i.region() +"</td>")
            f.write("<td>"+ i.country() +"</td>")
            f.write("<td>"+ i.location() +"</td>")
            f.write("<td>"+ i.hostname() +"</td>")
            f.write("</tr>")

        f.write("</table>")
        f.write("</body>")
        f.write("</html>")
        f.close()

# socket connection
class SocketConnection:
    def __init__(self, local_ip, local_port, remote_ip, remote_port, conn_type, status):
        self.local_ip = local_ip
        self.local_port = int(local_port)
        self.remote_ip = remote_ip
        self.remote_port = int(remote_port)
        self.conn_type = conn_type
        self.conn_status = status
        self.log_time =time.time()
    def __str__(self):
        return self.conn_status +"\t"+ self.local_ip + ':' + str(self.local_port) +"\t"+ self.remote_ip + ':' + str(self.remote_port)
    def connectionType(self):
        return self.conn_type
    def isExternal(self):
        return not self.isInternal()
    def isInternal(self):
        return NetworkUtils.is_internal(self.remote_ip)
    def localIPAddr(self):
        return self.local_ip + ':' + str(self.local_port)
    def remoteIPAddr(self):
        return self.remote_ip + ':' + str(self.remote_port)
    def localIP(self):
        return self.local_ip
    def localPort(self):
        return self.local_port
    def remoteIP(self):
        return self.remote_ip
    def remotePort(self):
        return self.remote_port
    def status(self):
        return self.conn_status
    def time(self):
        return self.log_time

def main():

    parser = argparse.ArgumentParser(description="NLabs.Studio Netmonitor Snapshot - Produce a report of TCP/UDP connections active on the (NIC) network interface card.")
    parser.add_argument('-m', type=int, required=False, help='number of minutes to sleep between each cycle - rate limit')
    parser.add_argument('-t', type=str, required=False, help='hexadecimal basic auth token for ipinfo.io API access with increased rate limit usage')
    parser.add_argument('-f', type=str, required=False, help='flag as non commercial - include the use of free to access non commercial suppliers')
    parser.add_argument('-x', type=str, required=False, help='flush the ip address information cache and export its contents to a CSV file')
    parser.add_argument('-mr', type=str, required=False, help='flag to produce multiple html report documents')
    parser.add_argument('-r', type=int, required=False, default=10, help='override the default refresh rate between cycles')
    parser.add_argument('-sp', type=str, help='perform a single connection sweet and terminate once complete')
    args = parser.parse_args()

    # perform a flush on the IP_AddressInfo cache
    if args.x:
        if os.path.isfile('info_cache'):
            try:
                cache_data = {}
                with open('info_cache', 'rb') as data_t:
                    cache_data = pickle.load(data_t)
                with open('ip_address_info', 'w') as f:
                    for key, c in cache_data.items():
                        f.write(str(c) +"\n")
                os.remove('info_cache')
                print('OK -> flush successful')
            except:
                print('processing error occurred')
        else:
            print('cache data file does not exist')
        return

    # multiple report flag
    mr = args.mr and args.mr.lower() == 'true'

    # not-commercial flag
    nc = args.f and args.f.lower() == 'true'

    # change the default refresh rate between cycles
    global g_refresh_interval
    g_refresh_interval = 10 if not args.r else args.r

    print("NLabs.Studio Netmonitor Snapshot Report Writer")
    print("CTRL+Q will terminate the process and return you to the command line prompt")
    time.sleep(5)

    while not g_quit_flag:

        live_list = psutil.net_connections()
        conn_list = {}

        # info list accomodates our geolocation cache data, if we have actively
        # ran our script before, we may have cache data available which reduces
        # the load on our third party suppliers 
        # 
        # each record is stored for q_query_days before forced update
        info_list = {}
        if os.path.isfile('info_cache'):
            try:
                with open('info_cache', 'rb') as data_t:
                    info_list = pickle.load(data_t)
            except:
                info_list = {}

        # foreach connection
        for c in live_list:

            # check for quit flag
            if g_quit_flag:
                break

            # skip if a remote host has not been ACKnowledged
            if not c.raddr:
                continue
            raddr = f"{c.raddr.ip}:{c.raddr.port}"

            # skip if remote connection is indeed internal on the LAN or a NAT proxy
            if NetworkUtils.is_internal(c.raddr.ip):
                continue

            # record connection
            conn_list[raddr] = SocketConnection(c.laddr.ip, c.laddr.port, c.raddr.ip, c.raddr.port, c.type, c.status)

            # determine if a requery is necessary to update the cache record
            requery = False
            if raddr in info_list:
                requery = info_list[raddr].logTime() < (time.time() - (g_requery_in_days * 86400))

            # no cache record exists or its time for a requery
            if raddr not in info_list or requery:

                # fetch geolocation data
                data_t = NetworkUtils.get_geolocation(c.raddr.ip, '' if not args.t else args.t, not nc)

                # third party fetch failed... init some defaults
                if data_t == None:
                    data_t = {}
                    data_t['ip'] = conn_list[raddr].remoteIP()
                    data_t['city'] = data_t['region'] = data_t['country'] = '*'

                # check hostname is available from third party, if not attempt to query it using a local socket
                if 'hostname' not in data_t:
                    data_t['hostname'] = NetworkUtils.reverse_dns(c.raddr.ip)
                    if data_t['hostname'] == None:
                        data_t['hostname'] = 'NA'

                # if longitude/latitude are not available, flag as '*'
                if 'loc' not in data_t:
                    data_t['loc'] = '*'

                # cache the geolocation data record
                info_list[raddr] = IP_AddressInfo(data_t['ip'], data_t['hostname'], data_t['city'], data_t['region'], data_t['country'], data_t['loc'])

            # some console noise - basic response
            print("-> "+ str(conn_list[raddr]))

        # serialise the cache data to disk
        with open('info_cache', 'wb') as data_t:
            pickle.dump(info_list, data_t)        

        # produce a readable report on active connections list
        ReportWriter.write(conn_list, info_list, mr)
        print("report generated - check localised directory for html document")

        # quit if triggered
        if g_quit_flag or args.sp:
            break

        # terminate or sleep depending on CL flag
        if args.m:
            print("repeating the process in "+ str(args.m) +" minutes")
            time.sleep(args.m*60)
        else:
            time.sleep(g_refresh_interval)

# kb hook and entry point
def _quit():
    global g_quit_flag
    g_quit_flag = True
    print('quit signal invoked...')
keyboard.add_hotkey('ctrl+q', _quit)
if __name__ == "__main__":
    main()
