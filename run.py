from gui import *
from PyQt4.QtGui import QFont
from uploader import *



class StartQT4(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.upload = uploader()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.setIcon()

        self.ui.singleMode.setChecked(True)
        self.lastState = "singleMode"
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
        self.connect(self.ui.singleMode,QtCore.SIGNAL("clicked()"), self.refreshList)
        self.connect(self.ui.groupMode,QtCore.SIGNAL("clicked()"), self.refreshList)
        
        self.ui.pushButton.clicked.connect(self.check)
        self.ui.pushButton_2.clicked.connect(self.uploadFile)
        self.ui.toolButton_2.clicked.connect(self.chooseFileToUpload)
        self.connect(self.ui.toolButton, QtCore.SIGNAL("clicked()"),self.updateESPlistWithThread)
        
    def updateESPlistWithThread(self):
        self.searchEspOnline = findEspOnlineThread(self.upload)
        self.connect(self.searchEspOnline, QtCore.SIGNAL("updateESPLIST()"),self.refreshList)
        self.connect(self.searchEspOnline, QtCore.SIGNAL("finished()"), self.done)
        self.searchEspOnline.start()
    
    
    def done(self):
        print "done"
        self.refreshList()
        self.updateESPlistWithThread()
#         self.refreshList()
        
    def refreshList(self):
        if self.ui.groupMode.isChecked() and self.lastState != "groupMode":
            self.zmien2()
        elif self.ui.singleMode.isChecked() and self.lastState != "singleMode":
            self.zmien1()
    def zmien1(self):
        print "zmien1"
        self.lastState = "singleMode"

        self.ui.comboBox.clear()
        for esp in self.upload.modules:
            print esp
            self.ui.comboBox.addItem(esp.type + " " + esp.mac,esp.ip)
    def zmien2(self):
        print "zmien2"
        self.lastState = "groupMode"

        self.ui.comboBox.clear()
        
        
        
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
            ans = serve(self.espIP, self.getLocalIP(), 8266, 13000, "", self.fileLocation, command = FLASH)
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
    
    