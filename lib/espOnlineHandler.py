# -*- coding: utf-8 -*-

import socket 
import nmap
import os
import hashlib
import logging
import sys
from PyQt4 import QtCore, QtGui
PORT = 8266

class esp(object):
    def __init__(self, data ):
        self.ip = data["ipv4"]
        self.mac = data["mac"]
        self.port = PORT
        
    def __eq__(self, module):
        if self.mac == module.mac:
            return True
        else: return False
        
    def __str__(self):
        return self.ip

class espOnline(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.modules = {}
        self.searcher = searchEspOnline()
        self.connect(self.searcher, QtCore.SIGNAL("newModule(PyQt_PyObject)"), self.addNew)
        self.connect(self.searcher, QtCore.SIGNAL("finished()"), self.done)
    
    def startSearching(self):
        self.searcher.start()
        
    def stopSearching(self):
        self.searcher.stop()
        
    def addNew(self,newModule):
        if newModule["mac"] not in self.modules:
            self.modules[newModule["mac"]] = newModule["ipv4"]
            self.emit(QtCore.SIGNAL("newModuleAdded()"))
    
    def done(self):
        self.startSearching()
    
    def getModules(self):
        return self.modules
    
    def getTypesList(self):
        return self.types.keys()
    
    def getModulesWithType(self, type):
        try:
            return self.types[type]
        except:
            return []
        
    def getIpList(self):
        return self.ipList
    

class uploader(QtCore.QThread):
    def __init__(self, module, fileToUpload, nr):
        sendingPORT = 13000
        QtCore.QThread.__init__(self)
        self.threadID = nr
        self.binFile = fileToUpload
        self.esp = module
        self.localPort = sendingPORT + nr
        
    def __del__(self):
        self.quit()
        self.wait()
        
    def run(self):
        self.emitInfo("start uploading.")
        ip = str(self.esp).split('@')[1]
        print ip
        self.serve(str(ip), self.getLocalIP(), str(PORT), str(self.localPort), "", str(self.binFile))
    def finished(self):
        self.emitTerminated()
    
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
        print "emitTerminated(%i)" % self.threadID
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
        server_address = (localAddr, int(localPort))
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
        self.emitInfo('Upload size: %d' % content_size)
        message = '%d %d %d %s\n' % (command, int(localPort), content_size, file_md5)
        
        self.emitInfo('Sending invitation to: %s' % remoteAddr)
        
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
                self.emitInfo('Result: %s' %data)
                connection.close()
                f.close()
                sock.close()
                if (data != "OK"):
                    self.emitError('%s' % data)
                    return 1;
                self.emitSuccess("done")
                self.emitTerminated()
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
        return 1
 

def logError(msg):
    print msg
    
def done():
    print "gotowe"
    
    
class searchEspOnline(QtCore.QThread):
    def __init__(self):
            QtCore.QThread.__init__(self)
            
            self.searchingTags = ["ESP", "MIC", "mic"]
            self.searchingPort =  "8266"
            self.scanner = nmap.PortScanner()
            self.nextAvailableIP = self.genNextIp()
            self.myIP = self.getLocalIP()
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
    
    def prepareIPrange(self,searchingRange = "1-255"):
        ip = self.getLocalIP().split(".")
        ip[-1] = searchingRange
        ip = ".".join(ip)
        return ip
    def addTag(self,tag):
        self.searchingTags.append(tag)
    def genNextIp(self):   
        self.scanner.scan(self.prepareIPrange(), self.searchingPort)
        print self.scanner.all_hosts()
        for item in self.scanner.all_hosts():
            if item == self.myIP: continue
            yield item
    def run(self):
        while True:
            try:
                ip = self.nextAvailableIP.next()
                print ip
                item = self.scanner.scan(ip, self.searchingPort, "-O", True)
                info =  item['scan'][ip]["addresses"]
                self.emit(QtCore.SIGNAL("newModule(PyQt_PyObject)"), info)
    
            except StopIteration:
                self.nextAvailableIP = self.genNextIp()
                
            except KeyError:
                pass

    def stop(self):
        self.runningFlag = False

        

if __name__ == "__main__":
    
    app = QtGui.QApplication(sys.argv)
    searcher = searchEspOnline()
    print searcher.start()
    print("gotowe")
    sys.exit(app.exec_())
    
    
    
