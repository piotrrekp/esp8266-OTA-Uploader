import socket
import nmap
import os
import hashlib
import logging
import sys
import time
from PyQt4 import QtCore, QtGui

class esp(object):
    def __init__(self, ip, hostname, port = 8266):
        self.ip = ip
        self.mac = ""
        self.type = ""
        self.port = port
        if hostname[:3] == "MIC":
            _, self.type,self.mac = hostname.split("_")
        else: 
            self.mac = "unknownMAC"
            self.type = "unknownType"
    def __str__(self):
        return self.type + self.ip

class espOnline(object):
    
    def __init__(self):
        self.modules = []
        self.types = {}
        self.ipList = []

    def addNew(self,newModule):
        if newModule.ip not in self.ipList:
            self.modules.append(newModule)
            self.ipList.append(newModule.ip)
        if newModule.type not in self.types:
            self.types[newModule.type] = []
            self.types[newModule.type].append(newModule)
        elif newModule.ip not in self.types[newModule.type]:
            self.types[newModule.type].append(newModule)
    def getModules(self):
        return self.modules
    def getTypes(self):
        return self.types.keys()
    def getModulesWithType(self,type):
        try:
            return self.types[type]
        except:
            return []
    def getIpList(self):
        return self.ipList
class uploader(object):
    def __init__(self):
        self.binFile = ""
        self._module = None
        self.modules = []
        self.types = {}
    @property
    def module(self):
        return self._module
 
    @module.setter
    def module(self, esp):
        self._module = esp
        self.modules.append(esp)
    def getLocalIP(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('10.255.255.255',0))
            IP = s.getsockname()[0] 
        except:
            self.getLocalIP()
        finally:
            s.close()
        return IP
    
    def prepareIPrange(self,searchingRange = "1-127"):
        ip = self.getLocalIP().split(".")
        ip[-1] = searchingRange
        ip = ".".join(ip)
        return ip
    
    def searchModules(self,port = "8266", tag = "ESP"):
        nm = nmap.PortScanner()
        ipRange = self.prepareIPrange()
        nm.scan(ipRange, port)
        for ip in nm.all_hosts():
            item = nm.scan(ip, port)    
            hostname = item['scan'][ip]["hostnames"][0]['name']
            if hostname[:3] in tag:
                foundedModule = esp(ip,hostname)
                self.addToModules(foundedModule)
                self.addToTypes(foundedModule)
    def addToModules(self, module):
        if module.ip not in [x.ip for x in self.modules]:
            self.modules.append(module)
    def addToTypes(self, module):
        if module.type not in self.types or  module not in self.types[module.type]:
            self.types[module.type] = [module]
           
        
    def setFileToUpload(self, filename):
        if os.path.isfile(filename) == False:
            raise IOError("File not found")
        elif  filename.split(".")[1] != "bin":
            raise IOError("Wrong type of file")
        else:
            self.binFile = filename
    
    
    def upload(self):
        localIP = self.getLocalIP()
        self.serve(self.module.ip, localIP, self.module.port, 17000, "", self.binFile , 0)
       
    def serve(self, remoteAddr, localAddr, remotePort, localPort, password, filename, command = 0):
        FLASH = 0
        SPIFFS = 100
        AUTH = 200
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (localAddr, localPort)
        logging.info('Starting on %s:%s', str(server_address[0]), str(server_address[1]))
        try:
            sock.bind(server_address)
            sock.listen(1)
        except:
            logging.error("Listen Failed")
            return 1
    
        content_size = os.path.getsize(filename)
        f = open(filename,'rb')
        file_md5 = hashlib.md5(f.read()).hexdigest()
        f.close()
        logging.info('Upload size: %d', content_size)
        message = '%d %d %d %s\n' % (command, localPort, content_size, file_md5)
    
        # Wait for a connection
        logging.info('Sending invitation to: %s', remoteAddr)
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        remote_address = (remoteAddr, int(remotePort))
        sent = sock2.sendto(message.encode(), remote_address)
        sock2.settimeout(10)
        try:
            data = sock2.recv(37).decode()
        except:
            logging.error('No Answer')
            sock2.close()
            return 1
        if (data != "OK"):
            if(data.startswith('AUTH')):
                nonce = data.split()[1]
                cnonce_text = '%s%u%s%s' % (filename, content_size, file_md5, remoteAddr)
                cnonce = hashlib.md5(cnonce_text.encode()).hexdigest()
                passmd5 = hashlib.md5(password.encode()).hexdigest()
                result_text = '%s:%s:%s' % (passmd5 ,nonce, cnonce)
                result = hashlib.md5(result_text.encode()).hexdigest()
                sys.stderr.write('Authenticating...')
                sys.stderr.flush()
                message = '%d %s %s\n' % (AUTH, cnonce, result)
                sock2.sendto(message.encode(), remote_address)
                sock2.settimeout(10)
                try:
                    data = sock2.recv(32).decode()
                except:
                    sys.stderr.write('FAIL\n')
                    logging.error('No Answer to our Authentication')
                    sock2.close()
                    return 1
                if (data != "OK"):
                    sys.stderr.write('FAIL\n')
                    logging.error('%s', data)
                    sock2.close()
                    sys.exit(1);
                    return 1
                sys.stderr.write('OK\n')
            else:
                logging.error('Bad Answer: %s', data)
                sock2.close()
                return 1
        sock2.close()
        logging.info('Waiting for device...')
        try:
            sock.settimeout(10)
            connection, client_address = sock.accept()
            sock.settimeout(None)
            connection.settimeout(None)
        except:
            logging.error('No response from device')
            sock.close()
            return 1
        try:
            f = open(filename, "rb")
            sys.stderr.write('Uploading')
            sys.stderr.flush()
            offset = 0
            while True:
                chunk = f.read(1460)
                if not chunk: break
                offset += len(chunk)
                connection.settimeout(10)
                try:
                    connection.sendall(chunk)
                    res = connection.recv(4)
                except:
                    sys.stderr.write('\n')
                    logging.error('Error Uploading')
                    connection.close()
                    f.close()
                    sock.close()
                    return 1
    
            sys.stderr.write('\n')
            logging.info('Waiting for result...')
            try:
                connection.settimeout(60)
                data = connection.recv(32).decode()
                logging.info('Result: %s' ,data)
                connection.close()
                f.close()
                sock.close()
                if (data != "OK"):
                    sys.stderr.write('\n')
                    logging.error('%s', data)
                    return 1;
                return 0
            except:
                logging.error('No Result!')
                connection.close()
                f.close()
                sock.close()
                return 1
    
        finally:
            connection.close()
            f.close()
        sock.close()
        logging.error("done")
        return 1
    
    

class test(QtCore.QObject):
    class tthread(QtCore.QThread):
        def __init__(self):
            QtCore.QThread.__init__(self)
            self.runningFlag = True
            self.i = self.gen()
        def __del__(self):
            self.wait()
        def gen(self):
            max = 127
            n = 0 
            while n < max:
                n += 1
                yield n
            
        def run(self):
            self.sleep(1)
            try:
                i = self.i.next()
            except StopIteration:
                self.i = self.gen()
            self.emit(QtCore.SIGNAL("NewModule(PyQt_PyObject)"),i)
            print "emit: ",i
        def stop(self):
            self.runningFlag = False
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.spis = []
        self.poszukiwacz = self.tthread()
        self.connect(self.poszukiwacz,QtCore.SIGNAL("NewModule(PyQt_PyObject)"), self.updateSpis)
        self.connect(self.poszukiwacz,QtCore.SIGNAL("finished()"), self.done)
    def stop(self):
        self.poszukiwacz.stop()
    def updateSpis(self,nowy):
        print "updateSpis"
        if nowy not in self.spis:
            self.spis.append(nowy)
        print self.spis
    def getSpis(self):
        return self.spis
    def start(self):
        self.poszukiwacz.start()
    def done(self):
        self.poszukiwacz.start()
        
if __name__ == "__main__":
    
#     upl.searchModules(tag = ["MIC","ESP"])
#     print len(upl.modules)
#     upl.searchModules(tag = ["MIC","ESP"])
#     print len(upl.modules)
# 
#     print upl.types
  
    app = QtGui.QApplication(sys.argv)
    obj = test()
    obj.start()
    i = 0 
    sys.exit(app.exec_())
