import socket
import sys
import os
from datetime import datetime

class clientLogic():
    def __init__(self):
        
        #servIP = socket.gethostbyname(sys.argv[1])
        self.locIP = socket.gethostbyname(socket.gethostname())
        self.servIP = self.locIP
        self.servPort = 21
        self.clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clientSock.connect((self.servIP, self.servPort))
        self.binaryFile = False
        self.passive = True
        self.passiveServerPort = self.servPort
        self.passiveServerIP = self.servIP
        self.baseDirectory = os.path.abspath('./clientDirectory')

    def getReply(self):
        echoSentence = self.clientSock.recv(1024)
        print 'Response:', echoSentence
        print ("")

 # access control commands ---------------------------------------

    def USER(self, username):
        # USER <SP> <username> <CRLF>
        # username - string
        self.clientSock.send('USER '+username)
        self.getReply()

    def PASS(self, password):
        # PASS <SP> <password> <CRLF>
        # password - string
        self.clientSock.send('PASS '+password)
        self.getReply()

    def CWD(self, directory):
        self.clientSock.send('CWD  ' + directory)
        self.getReply()
    
    def CDUP(self):
        self.clientSock.send('CDUP\r\n')
        self.getReply()

    def QUIT(self):
        # QUIT <CRLF>
        self.clientSock.send('QUIT \r\n')
        self.getReply()

    # transfer parameter commands -----------------------------------

    def PORT(self, ipAddr, port):

        IPChunks = ipAddr.split('.')
        byteU = int(port / 256)
        byteL = port % 256

        connectionString = '%s,%i,%i' % (','.join(IPChunks[:4]), byteU, byteL)
        self.passive = False

        self.activeSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.activeSocket.bind((ipAddr, port))
        self.activeSocket.listen(1)
        self.clientSock.send('PORT '+connectionString)

        print 'Port connection opened at address %s:%u\n' % (ipAddr, port)

        self.getReply()

    def PASV(self):
        self.clientSock.send('PASV \r\n')
        reply = self.clientSock.recv(1024)
        print 'Response:', reply
        openBracketIndex = reply.find('(')
        closeBracketIndex = reply.find(')')

        connectionString = reply[openBracketIndex+1:-(len(reply) - closeBracketIndex)]

        rec = connectionString.split(',')
        self.passiveServerIP = '.'.join(rec[:4])

        byteU = int(rec[4])
        byteL = int(rec[5])
        self.passiveServerPort = 256*byteU + byteL

        print 'Connecting to server address %s:%u\n' % (self.passiveServerIP, self.passiveServerPort)

        self.passive = True

    def TYPE(self, fileName):
        # TYPE <SP> <type-code> <CRLF>

        if fileName.find('.') != -1:
            if fileName.find('.txt') != -1 or \
                fileName.find('.html') != -1 or \
                fileName.find('.pl') != -1 or \
                fileName.find('.cgi') != -1:
                self.binaryFile = False
                self.clientSock.send('TYPE A')
            else:
                self.binaryFile = True
                self.clientSock.send('TYPE I')
        else:
            print 'Specified type not recognised'
            return
        
        self.getReply()

    def STRU(self, structureCode):
        self.clientSock.send('STRU '+structureCode)
        self.getReply()

    def MODE(self, transferMode):
        self.clientSock.send('MODE '+transferMode)
        self.getReply()

    
    # service commands -----------------------------------------------

    def RETR(self, fileName):
        # receive a copy file over data connection
    
        self.clientSock.send('RETR '+fileName)

        self.open_dataSocket()

        filePath = os.path.join(self.baseDirectory, fileName)
        
        if self.binaryFile:
            requestedFile = open(filePath,'wb')
        else :
            requestedFile = open(filePath,'w')

        dataChunk = self.dataStreamSocket.recv(1024)
        while (dataChunk):
            print "Receiving..."
            requestedFile.write(dataChunk)
            dataChunk = self.dataStreamSocket.recv(1024)

        requestedFile.close()
        print "Done Receiving"
        self.dataStreamSocket.close()

        response = self.clientSock.recv(1024)
        print response

        if response[:3] == '226':
            print 'successful'
        elif response[:3] == '451' or response[:3] == '550':
            print 'File trainsfer failed'
            if os.path.exists(filePath):
                os.remove(filePath)
        else:
            print 'Unknown transfer error occured'

    def STOR(self, fileName):
        
        # send data across data connection to store as file on server
        filePath = os.path.join(self.baseDirectory, fileName)

        if os.path.exists(filePath):
            self.clientSock.send('STOR '+fileName)
        else:
            print 'File not found'
            return

        self.open_dataSocket()
        
        if self.binaryFile:
            requestedFile = open(filePath,'rb')
        else :
            requestedFile = open(filePath,'r')
            
        fileChunk = requestedFile.read(1024)

        while fileChunk:
            print 'Sending...'
            self.dataStreamSocket.send(fileChunk)
            fileChunk = requestedFile.read(1024)

        requestedFile.close()
        self.dataStreamSocket.shutdown(socket.SHUT_WR)

        print "Done Sending"

        response = self.clientSock.recv(1024)
        print response

    def open_dataSocket(self):

        if self.passive:
            self.dataStreamSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
            reply = self.clientSock.recv(1024)
            print 'Response:', reply 
            if reply[:3] == '150':
                self.dataStreamSocket.connect((self.passiveServerIP, self.passiveServerPort))
            else:
                return
        else:
            reply = self.clientSock.recv(1024)
            print 'Response:', reply 
            self.dataStreamSocket, addr = self.activeSocket.accept()
    
    def close_dataSocket(self):
        if self.passive == False:
            self.activeSocket.close()
        self.dataStreamSocket.close()
    
    def PWD(self):
        self.clientSock.send('PWD \r\n')
        self.getReply()

    def LIST(self):
        self.clientSock.send('LIST \r\n')

        self.open_dataSocket()

        directoryArray = [] 
        directoryItem = self.dataStreamSocket.recv(1024)
        directories = ''

        while (directoryItem):
            directories += directoryItem
            directoryItem = self.dataStreamSocket.recv(1024)
            
        directoryArray = directories.split('\n')
        for i in range(0,len(directoryArray)):
            print directoryArray[i]
            if directoryArray[i].strip() == '':
                del directoryArray[i]
            
        print 'Number of items in directory:',len(directoryArray)
        print "Done Receiving"

        if len(directoryArray) == 0:
            print 'Directory empty...'

        self.getReply()
    
    def NOOP(self):
        self.clientSock.send('NOOP\r\n')
        self.getReply()