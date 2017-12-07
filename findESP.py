import socket
import os
import sys
import time
import nmap
import logging
import hashlib

# Commands
FLASH = 0
SPIFFS = 100
AUTH = 200

def serve(remoteAddr, localAddr, remotePort, localPort, password, filename, command = FLASH):
    # Create a TCP/IP socket
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

def getLocalIP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255',0))
        IP = s.getsockname()[0] 
    except:
        getLocalIP()
    finally:
        s.close()
    return IP

def prepareIPforScanning(IP):
    ip = IP.split(".")
    ip[-1] = "1"
    ip = ".".join(ip)
    return ip

def scanIPforEsp(lastOctet):
    _octets = getLocalIP().split(".")
    _octets[-1] = str(lastOctet)
    ip = ".".join(_octets)
    nm = nmap.PortScanner()
    result = nm.scan(ip, "8266")
    return result
    
    key = ip
    print key
    if result["scan"][key]['hostnames'][0]['name'][:3] in [ "ESP", "MICON"]:
        print key
        return result["scan"][key]['hostnames'][0]['name'] + " " + key
    else:
        return " "
    
def scanNetworkWithNmap():
    espList = "" 
    nm = nmap.PortScanner()
    ipRange = prepareIPforScanning(getLocalIP()) +"-127"
    result =  nm.scan(ipRange, "8266")
    hosty = result['scan']
    for key in hosty:
        if hosty[key]['hostnames'][0]['name'][:3] in [ "ESP", "MIC"]:
            espList += " " + hosty[key]['hostnames'][0]['name'] + ":" + key
    return espList

if __name__ == '__main__':
    print(getLocalIP())
    foundedESP =  scanNetworkWithNmap()
    print len(foundedESP)
    print foundedESP
    print('uploading...')
#     serve("192.168.1.49", getLocalIP(), 8266, 13000, "", "THP.bin", command = FLASH)
    print "\t...done"
#     for i in range(1,127):
#         print scanIPforEsp(i)
    
    
    
    
    