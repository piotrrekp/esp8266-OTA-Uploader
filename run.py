from gui import *
from findESP import *
from PyQt4.QtGui import QFont

        
class esp(object):
    def __init__(self, ip, hostname):
        self.ip = ip
        self.mac = ""
        self.type = ""
        if hostname[:3] == "MIC":
            _, self.type,self.mac = hostname.split("_")
        else: 
            self.mac = "unknown"
            self.type = "unknown"

class findEspOnlineThread(QtCore.QThread):

    def __init__(self):
        self.espOnline = ""
        QtCore.QThread.__init__(self)
    def __del__(self):
        self.wait()
    def run(self):
        self.espOnline = scanNetworkWithNmap()
        self.emit(QtCore.SIGNAL("updateESPLIST(QString)"),self.espOnline)
        pass
    
class StartQT4(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.setIcon()
        
        self.ui.singleMode.setChecked(True)
        self.ui.pushButton_2.setVisible(False)
        self.availableESP = {}
        self.ui.comboBox.addItem("Wait until scan ending")
        self.ui.pushButton.setText("Check")
        self.ui.pushButton_2.setText("Upload")
        self.ui.textEdit.setColor(QtGui.QColor("yellow"))
        self.ui.textEdit.setFont(QtGui.QFont("Times",12, QFont.Bold))
        
        self.updateESPlistWithThread()
        self.initSignals()
        self.binFile = ""
    
    def setIcon(self):
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("img/refresh.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.toolButton.setIcon(icon)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap("img/files-selection.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.toolButton_2.setIcon(icon1)
    
    def initSignals(self):
        self.ui.pushButton.clicked.connect(self.check)
        self.ui.pushButton_2.clicked.connect(self.uploadFile)
        self.ui.toolButton_2.clicked.connect(self.chooseFileToUpload)
        self.connect(self.ui.toolButton, QtCore.SIGNAL("clicked()"),self.updateESPlistWithThread)
        
    def updateESPlistWithThread(self):
       
        self.searchEspOnline = findEspOnlineThread()
        self.connect(self.searchEspOnline, QtCore.SIGNAL("updateESPLIST(QString)"),self.zmien)
        self.connect(self.searchEspOnline, QtCore.SIGNAL("finished()"), self.done)
        self.searchEspOnline.start()
    
    
    def done(self):
        print "ok"
        
    
    def zmien(self, espOnline):
        self.ui.comboBox.clear()
        self.availableESP = {}
        self.availableESPtmp = espOnline.split(" ")
        for item in self.availableESPtmp:
            try: 
                name,ip = item.split(":")
            except:
                continue
            self.availableESP[str(name)] = str(ip)
            self.ui.comboBox.addItem(name,ip)
    
    def chooseFileToUpload(self):
        self.binFile = QtGui.QFileDialog.getOpenFileName(None, "Choose file to upload", ".","Bin files (*.bin)")
        self.ui.lineEdit.setText(self.binFile)
    
    def check(self):
        self.espIP = self.ui.comboBox.currentText()
        self.fileLocation = self.ui.lineEdit.text()
        print self.availableESP
        config = "Destination module type: "
        config += self.espIP
        config += " at "
        config += self.availableESP[str(self.espIP)] 
        config += "\n"
        config += "File to Upload: "
        config += ".../"+"/".join(str(self.fileLocation).split("/")[-2:])
        config += "\n"
        self.ui.textEdit.setText(config) 
        
        self.ui.pushButton_2.setVisible(True)
        
    def uploadFile(self):
        try:
            ans = serve(self.espIP, getLocalIP(), 8266, 13000, "", self.fileLocation, command = FLASH)
            if ans == 1:
                tekst = "There was some unexpected error. Please restart module and try again."
                self.ui.textEdit.setColor(QtGui.QColor("red"))
            else:
                tekst = "Uploading done!"
                self.ui.textEdit.setColor(QtGui.QColor("green"))
            self.ui.textEdit.append(tekst)
        except OSError as e:
            tekst = "There was some error: " + str(e)
            self.ui.textEdit.setColor(QtCore.QColor("red"))
            self.ui.textEdit.setText(tekst)
            
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    myapp = StartQT4()
    myapp.show()
    sys.exit(app.exec_())
    
    