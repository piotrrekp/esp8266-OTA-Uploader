import socket
import nmap
import os
import hashlib
import logging
import sys
import time
from PyQt4 import QtCore, QtGui
import new
from __builtin__ import file

class esp(object):
    def __init__(self, ip, hostname, port = 8266):
        self.ip = ip
        self.mac = ""
        self.type = ""
        self.port = port
        if hostname[:3] == "MIC":
            _, self.type,self.mac = hostname.split("_")
            self.toStr = self.type + " " +  self.mac
        elif hostname[:3] == "ESP":
            self.type = "unknownType"
            self.mac = "unknownMac"
            self.toStr = hostname + " " + self.ip
        else: 
            self.mac = "unknownMAC"
            self.type = "unknownType"
            self.toStr = "unknownModule" + " " + self.ip
    def __str__(self):
        return self.toStr

class espOnline(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.modules = []
        self.types = {}
        self.ipList = []
        self.searcher = searchEspOnline()
        self.connect(self.searcher, QtCore.SIGNAL("newModule(PyQt_PyObject)"), self.addNew)
        self.connect(self.searcher, QtCore.SIGNAL("finished()"), self.done)
    def startSearching(self):
        self.searcher.start()
    def stopSearching(self):
        self.searcher.stop()
    def addTag(self, tag):
        self.searcher.addTag(tag)
    def addNew(self,newModule):
        if newModule.ip  not in self.ipList:
            self.ipList.append(newModule.ip)
            self.modules.append(newModule)
            self.emit(QtCore.SIGNAL("newModuleAdded()"))
            if newModule.type == "unknownType": 
                return
            if newModule.type not in self.types:
                self.types[newModule.type] = []
                self.types[newModule.type].append(newModule)
            elif newModule.ip not in self.types[newModule.type]:
                self.types[newModule.type].append(newModule)
    def done(self):
        self.startSearching()
    def getModules(self):
        return self.modules
    def getTypesList(self):
        return self.types.keys()
    def getModulesWithType(self,type):
        try:
            return self.types[type]
        except:
            return []
    def getIpList(self):
        return self.ipList
    
class searchEspOnline(QtCore.QThread):
    def __init__(self):
            QtCore.QThread.__init__(self)
            
            self.searchingTags = ["ESP"]
            self.searchingPort =  "8266"
            self.scanner = nmap.PortScanner()
            self.nextAvailableIP = self.genNextIp()
    def __del__(self):
        self.wait()
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
    def addTag(self,tag):
        self.searchingTags.append(tag)
    def genNextIp(self):   
        self.scanner.scan(self.prepareIPrange(), self.searchingPort)
        for item in self.scanner.all_hosts():
            yield item
    def run(self):
        try:
            ip = self.nextAvailableIP.next()
            item = self.scanner.scan(ip, self.searchingPort)
            hostname = item['scan'][ip]["hostnames"][0]['name']
            if hostname[:3] in self.searchingTags:
                foundedModule  = esp(ip, hostname)
                self.emit(QtCore.SIGNAL("newModule(PyQt_PyObject)"), foundedModule)
        except StopIteration:
            self.nextAvailableIP = self.genNextIp()
        except KeyError:
            pass

    def stop(self):
        self.runningFlag = False
        


class uploader(QtCore.QThread):
    def __init__(self, module, fileToUpload, nr):
        PORT = 13000
        QtCore.QThread.__init__(self)
        self.threadID = nr
        self.binFile = fileToUpload
        self.esp = module
        self.localPort = PORT + nr
        
    def __del__(self):
        self.wait()
        
    def run(self):
        self.emitInfo("start uploading.")
        self.emitError("testowy error")
        self.emitSuccess("testowy success")
#         self.serve(self.esp.ip, self.getLocalIP(), self.esp.port, str(self.localPort), "", self.binFile)
        
        
        self.emitTerminated()
        pass
    
    def emitInfo(self, msg):
        msg = str (self.esp) + ": " + msg
        logging.info(msg)
        self.emit(QtCore.SIGNAL("info(PyQt_PyObject)"), msg)
    
    def emitError(self, msg):
        msg = str (self.esp) + ": " + msg
        logging.info(msg)
        self.emit(QtCore.SIGNAL("error(PyQt_PyObject)"), msg)
        self.terminate()
    
    def emitSuccess(self, msg):
        msg = str (self.esp) + ": " + msg
        logging.info(msg)
        self.emit(QtCore.SIGNAL("success(PyQt_PyObject)"), msg)
    
    def emitTerminated(self):
        self.emit(QtCore.SIGNAL("exit(PyQt_PyObject)"),self.threadID)
        
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
    
    def serve(self, remoteAddr, localAddr, remotePort, localPort, password, filename, command = 0):
        FLASH = 0
        SPIFFS = 100
        AUTH = 200
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (localAddr, localPort)
        try:
            sock.bind(server_address)
            sock.listen(1)
        except:
            
            self.emitError("Listen Failed")
            return 1
    
        content_size = os.path.getsize(filename)
        f = open(filename,'rb')
        file_md5 = hashlib.md5(f.read()).hexdigest()
        f.close()
        self.emitInfo('Upload size: %d', content_size)
        message = '%d %d %d %s\n' % (command, localPort, content_size, file_md5)
        
        self.emitInfo('Sending invitation to: %s', remoteAddr)
        
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        remote_address = (remoteAddr, int(remotePort))
        sent = sock2.sendto(message.encode(), remote_address)
        sock2.settimeout(10)
        try:
            data = sock2.recv(37).decode()
        except:
            sock2.close()
            self.emitError('No Answer')
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
                    sock2.close()
                    self.emitError('FAIL\nNo Answer to our Authentication')
                    return 1
                if (data != "OK"):
                    sock2.close()
                    self.emitError('FAIL\n%s', data)
                    return 1
                self.emitInfo('OK\n')
            else:
                sock2.close()
                self.emitError('Bad Answer: %s', data)
                return 1
        sock2.close()
        self.emitInfo('Waiting for device...')
        try:
            sock.settimeout(10)
            connection, client_address = sock.accept()
            sock.settimeout(None)
            connection.settimeout(None)
        except:
            sock.close()
            self.emitError('No response from device')
            return 1
        try:
            f = open(filename, "rb")
            
            self.emitInfo('Uploading')
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
                    connection.close()
                    f.close()
                    sock.close()
                    self.emitError('Error Uploading')
                    return 1
    
            self.emitInfo('Waiting for result...')
            try:
                connection.settimeout(60)
                data = connection.recv(32).decode()
                self.emitInfo('Result: %s' ,data)
                connection.close()
                f.close()
                sock.close()
                if (data != "OK"):
                    self.emitError('%s', data)
                    return 1;
                return 0
            except:
                connection.close()
                f.close()
                sock.close()
                self.emitError('No Result!')
                return 1
    
        finally:
            connection.close()
            f.close()
        sock.close()
        self.emitSuccess("done")
        self.emitTerminated()
        return 1
 

    
if __name__ == "__main__":
    
    
    app = QtGui.QApplication(sys.argv)
    moduly = espOnline()
    nowy = esp("192.168.1.28", "MIC_THP_AA:BB:CC:DD:EE:FF")
    
    moduly.addNew(nowy)
    nowy = esp("192.168.1.29", "ESP_AABBCSA")
    
    moduly.addNew(nowy)
    nowy = esp("192.168.1.31", "MIC_THP_AA:BB:CC:DD:EE:FF")
    moduly.addNew(nowy)
    nowy = esp("192.168.1.31", "MIC_THP_UU:BB:CC:DD:EE:FF")
    
    moduly.addNew(nowy)
    
    print moduly.getTypesList()
    
    print "moduly THP: ", ",".join(map(str,moduly.getModulesWithType("THP")))
    
    print "wszystkie moduly: "," , ".join(map(str,moduly.getModules()))
    
    sys.exit(app.exec_())
    
    
    
