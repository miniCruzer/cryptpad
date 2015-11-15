#!/usr/bin/env python
##
## Copyright (C) 2015 Samuel Hoffman
##
## Cryptpad -- notepad, but encrypts and decrypts files.
##
import sip
sip.setapi("QString", 2)
sip.setapi("QVariant", 2)

import sys, os, shutil

try:
    from cStringIO import StringIO 
except ImportError:
    from StringIO import StringIO

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from Crypto.Cipher import AES
from Crypto.Hash import SHA256, HMAC
from Crypto.Random.random import randint
import bcrypt

from ui_cryptpad import Ui_MainWindow

MAC_SIZE = SHA256.digest_size

class AuthenticationError(Exception):
    pass


def encrypt(data, Ek, Ak):
    """Encrypt then MAC"""

    ## encrypt

    clear = StringIO(data)

    print("Ek is length %d" % len(Ek))
    iv = ''.join(chr(randint(0, 0xFF)) for i in range(16))
    encryptor = AES.new(Ek, AES.MODE_CBC, iv)

    clear.seek(0)
    crypted = StringIO()

    crypted.write(iv)
    while True:
        chunk = clear.read(16)

        if len(chunk) == 0:
            break
        elif len(chunk) % 16 != 0:
            chunk += ' ' * (16 - len(chunk) % 16)

        crypted.write(encryptor.encrypt(chunk))

    ## then mac

    h = HMAC.new(Ak, crypted.getvalue(), digestmod=SHA256)
    crypted.write(h.digest())
    crypted.seek(0)

    return crypted

class MainWindow(QMainWindow, Ui_MainWindow):

    currentDocument = None
    autoSaveTimer = None
    dataSinceLastSave = ''
    Ekey = None
    Akey = None

    def __init__(self):

        super(MainWindow, self).__init__()
        self.setupUi(self)

        self.setupActions()

    def setupActions(self):
        self.actionSave.triggered.connect(self.saveDocument)
        self.actionSave_As.triggered.connect(self.saveDocumentAs)
        self.actionNew.triggered.connect(self.newDocument)
        self.textEdit.textChanged.connect(self.changesMade)
        self.actionOpen.triggered.connect(self.openDocument)
        self.actionFont.triggered.connect(self.selectFont)

    def changesMade(self):
        """triggered when text is changed"""
        if self.textEdit.toPlainText() != self.dataSinceLastSave:
            return True
        return False

    def selectFont(self):
        self.textEdit.setFont(QFontDialog.getFont(self.textEdit.font(), self)[0])

    def saveDocument(self):
        if self.currentDocument == None:
            self.saveDocumentAs()
        else:
            self.encryptThenSave(self.currentDocument)

    def openDocument(self):
        fileName = QFileDialog.getOpenFileName(self, "Open File")
        if fileName:

            self.decryptThenOpen(fileName)

    def newDocument(self):
        res = self.promptSaveChanges()
        if res == QMessageBox.Save:
            self.saveDocument()
        elif res == QMessageBox.Discard:
            self.textEdit.setPlainText("")
            self.key = None
        else:
            return ## cancel new doc

    def promptSaveChanges(self):
        if self.changesMade():
            res = QMessageBox.question(self, "Save Changes", "There are unsaved changes in the editor. Would you like to save those now?", QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            return res

    def saveDocumentAs(self):
        fileName = QFileDialog.getSaveFileName(self, "Save As")
        if fileName:
            self.encryptThenSave(fileName)
        
    def encryptThenSave(self, fileName):
        if not self.Ekey:
            self.Ekey, self.Akey = self.promptEncrytptionPhrase()

        doc = self.textEdit.toPlainText()
        enc = encrypt(doc, self.Ekey, self.Akey)

        with open(fileName, 'wb') as outFile:
            shutil.copyfileobj(enc, outFile)
        
        self.currentDocument = fileName
        self.statusbar.showMessage("Save complete.", 3000)

    def decryptThenOpen(self, fileName):
        Ek, Ak = self.promptEncrytptionPhrase()
        
        if not Ek:
            return

        with open(fileName, 'rb') as inFile:

            #key = self.promptEncrytptionPhrase()
            crypted = inFile.read()

            data = crypted[:-MAC_SIZE]

            mac = crypted[-MAC_SIZE:]
            real_mac = HMAC.new(Ak, data, SHA256).digest()
            if mac != real_mac:
                retval = QMessageBox.critical(self, "Authentication Error", "HMAC signature in file does not match acutal HMAC.<br>"
                    "Either you entered the wrong passphrase, or the file has been tampered with.<br><br>"
                    "Would you like to attempt to decrypt anyway?", QMessageBox.Yes | QMessageBox.No)
                if retval == QMessageBox.No:
                    return

            ## auth passed, prepare for decryption
            iv = crypted[:16]
            decryptor = AES.new(Ek, AES.MODE_CBC, iv)
            decrypted = StringIO()
            handle = StringIO(crypted[16:-MAC_SIZE])

            while True:
                chunk = handle.read(16)
                if len(chunk) < 16:
                    break
                decrypted.write(decryptor.decrypt(chunk))

        self.textEdit.setPlainText(decrypted.getvalue())

    def promptEncrytptionPhrase(self):

        phrase, ok = QInputDialog.getText(self, "Encryption Phrase", "Enter a passphrase with which to encrypt this file.",
            QLineEdit.Password, "")

        if ok:
            Ek = SHA256.new(phrase.encode()).digest()
            Ak = SHA256.new(Ek).digest()

            return Ek, Ak

    def closeEvent(self, event):
        res = self.promptSaveChanges()
        if res == QMessageBox.Save:
                self.saveDocument()
        elif res == QMessageBox.Discard:
            self.textEdit.setPlainText("")
            self.changesMade = False
        elif res == QMessageBox.Cancel:
            event.ignore()

def main():

    app = QApplication(sys.argv)

    mw = MainWindow()
    mw.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
