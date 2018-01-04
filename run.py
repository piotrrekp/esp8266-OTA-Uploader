from gui import *
from PyQt4.QtGui import QFont
from lib import espOnlineHandler
import  sys, os
from PyQt4.Qt import QString, QColor
    
class StartQT4(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        
        self.uploadMode = 1
        self.modulesToUpload = []
        self.binFile = ""

        self.ui = Ui_ESP8266Uploader()
        self.ui.setupUi(self)
        self.ui.groupMode.setEnabled(False)

        self.setIcon()
        self.initSignals()
        self.initSearcher()
        
        self.dssListOfModule = self.ui.listOfModules.styleSheet()
        self.dssfilePath = self.ui.filePath.styleSheet()
        
    def setIcon(self):
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("img/files-selection.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.searchFilePath.setIcon(icon)
        
    def initSignals(self):
        self.connect(self.ui.singleMode, QtCore.SIGNAL("toggled(bool)"), self.clickedSignleModule)
        self.connect(self.ui.groupMode, QtCore.SIGNAL("toggled(bool)"), self.clickedGroupModule)
        self.connect(self.ui, QtCore.SIGNAL("updateModuleList(PyQt_PyObject)"),self.updateModuleList)
        self.connect(self.ui.listOfModules, QtCore.SIGNAL("activated(int)"),self.setModuleToUpload)
        self.connect(self.ui.uploadButton, QtCore.SIGNAL("clicked()"),self.serve)
        self.connect(self.ui.searchFilePath, QtCore.SIGNAL("clicked()"),self.searchFileToUpload)
        self.connect(self, QtCore.SIGNAL("checkUploadersList()"), self.checkUploaders)
    
    def searchFileToUpload(self):
        self.binFile = QtGui.QFileDialog.getOpenFileName(parent=None, caption=QString(), filter = "Bin files(*.bin)")
        self.ui.filePath.setText(self.binFile)
        pass
    
    def setModuleToUpload(self, nr):
        self.modulesToUpload = []
        if self.uploadMode == 1:
            module = self.ui.listOfModules.itemData(nr).toPyObject()
            print module
            print type(module)
            self.modulesToUpload = [module]
            self.logInfo("Selected module: %s" % ( str(module)))
        elif self.uploadMode == 2:
            self.modulesToUpload = list(self.ui.listOfModules.itemData(nr).toPyObject())
            typeOfMoudle = self.ui.listOfModules.currentText()
            self.logInfo("Selected modules type: %s" % (typeOfMoudle))
        
    def logInfo(self,msg):
        self.ui.logger.setFontWeight(50)
        self.ui.logger.setColor(QColor("white"))
        self.ui.logger.append(msg)
    
    def logError(self,msg):
        self.ui.logger.setFontWeight(90)
        self.ui.logger.setColor(QColor("red"))
        self.ui.logger.append(msg)
        self.ui.listOfModules.clear()
        self.modulesToUpload = []
        self.ui.uploadButton.setEnabled(True)
    def logSuccess(self,msg):
        self.ui.logger.setFontWeight(64)
        self.ui.logger.setColor(QColor("green"))
        self.ui.logger.append(msg)
        
    def clickedSignleModule(self,state):
        if state: self.ui.emit(QtCore.SIGNAL("updateModuleList(PyQt_PyObject)"),1)

    def clickedGroupModule(self,state):
        if state: self.ui.emit(QtCore.SIGNAL("updateModuleList(PyQt_PyObject)"),2)
    
    def updateModuleList(self, mode):
        if mode == 1:
            self.uploadMode = 1
            self.logInfo("Single Mode")
            self.updateAvailableEsp()
        elif mode == 2:
            self.uploadMode = 2
            self.logInfo("Multi Mode")
            self.updateAvailableEsp()
            
    def serve(self):
        errorSum = 0
        self.logInfo("Checking the correctness of selected items")

        if not self.modulesToUpload:
            errorSum += 1
            self.logError("Module to upload not selected !!!")
            self.ui.listOfModules.setStyleSheet("border: 2px solid red;")

        else:
            self.ui.listOfModules.setStyleSheet(self.dssListOfModule)
            if self.uploadMode == 1:
                self.logSuccess("Module to upgrade firmware: %s" % (self.modulesToUpload[0]))
        
            elif self.uploadMode == 2:
                self.logSuccess("Modules type to upgrade firmware: %s" % (self.modulesToUpload[0].type))
        self.binFile = self.ui.filePath.text()
        if not self.binFile:
            errorSum += 1
            self.logError("File to upload not selected !!!")
            self.ui.filePath.setStyleSheet("border: 2px solid red;")

        elif os.path.isfile(self.binFile) == False:
            errorSum += 1
            self.logError("File not found !!!")
            self.ui.filePath.setStyleSheet("border: 2px solid red;")
        
        else:
            self.logSuccess("File selected to upload: %s" % (self.binFile))
            self.ui.filePath.setStyleSheet(self.dssfilePath)
        
        if errorSum == 0:
            self.startUploadingProcess()
        
    def startUploadingProcess(self):
        self.ui.uploadButton.setEnabled(False)
        self.uploaders = {}
        i = 0
        for item in self.modulesToUpload:
            uploader = espOnlineHandler.uploader(item, self.binFile, i)
            self.logInfo("thread number %d: %s" % (i,str(uploader)))
            self.connect(uploader, QtCore.SIGNAL("error(PyQt_PyObject)"), self.logError)
            self.connect(uploader, QtCore.SIGNAL("info(PyQt_PyObject)"), self.logInfo)
            self.connect(uploader, QtCore.SIGNAL("success(PyQt_PyObject)"), self.logSuccess)
            self.connect(uploader, QtCore.SIGNAL("exit(PyQt_PyObject)"), self.removeThread)
            self.connect(uploader, QtCore.SIGNAL("finished()"),self.done)
            uploader.start()
            self.uploaders[i] = uploader
            i += 1
      
    def removeThread(self, nr):
        if nr in self.uploaders:
            self.uploaders.pop(nr)
        self.emit(QtCore.SIGNAL("checkUploadersList()"))
        
    def done(self):
        self.logSuccess("Upload finished with SUCCESS!")  
        self.emit(QtCore.SIGNAL("checkUploadersList()"))
        
    def checkUploaders(self):
        if not self.uploaders: 
            self.ui.uploadButton.setEnabled(True) 
        else:
            self.logInfo(",".join(map(str,self.uploaders.keys())))
            
    def initSearcher(self):
        self.logInfo("Start searching available modules")
        self.searcher = espOnlineHandler.espOnline()
        self.connect(self.searcher, QtCore.SIGNAL("newModuleAdded()"), self.addNewModule)
        self.searcher.startSearching()
    
    def addNewModule(self):
        self.logSuccess("New module founded")
        self.updateAvailableEsp()
    
    def updateAvailableEsp(self):
        self.ui.listOfModules.clear()
        if self.uploadMode == 2:
            for item in self.searcher.types:
                self.ui.listOfModules.addItem(item,QtCore.QVariant(self.searcher.getModulesWithType(item)))
        elif self.uploadMode == 1:
            for item in self.searcher.modules:
                module = item + " @ " + self.searcher.modules[item]
                self.ui.listOfModules.addItem(module, QtCore.QVariant(module))
            if not self.modulesToUpload:
                self.modulesToUpload.append(self.ui.listOfModules.itemData(0).toPyObject())
        self.ui.listOfModules.update()
                
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    myapp = StartQT4()
    myapp.show()
    sys.exit(app.exec_())
    
    