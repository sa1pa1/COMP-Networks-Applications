# Include the libraries for socket and system calls
# sally: Identifying the interactions in step 1 and 2. 
import socket
import sys
import os
import argparse
import re
#sally: 
# 1MB buffer size
BUFFER_SIZE = 1000000

# Get the IP address and Port number to use for this web proxy server
# sally: Step 2.2: Port number the proxy will be on. 
parser = argparse.ArgumentParser()
parser.add_argument('hostname', help='the IP Address Of Proxy Server')
parser.add_argument('port', help='the port number of the proxy server')
args = parser.parse_args()
proxyHost = args.hostname
proxyPort = int(args.port)

# Create a server socket, bind it to a port and start listening
try:
  # Create a server socket
  # ~~~~ INSERT CODE ~~~~
  #from https://docs.python.org/2.7/library/socket.html in creating a socket 
  Server_Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  # ~~~~ END CODE INSERT ~~~~
  print ('Created socket')
except:
  print ('Failed to create socket')
  sys.exit()

try:
  # Bind the the server socket to a host and port
  # ~~~~ INSERT CODE ~~~~
  Server_Socket.bind((proxyHost, proxyPort))
  # ~~~~ END CODE INSERT ~~~~
  print ('Port is bound')
except:
  print('Port is already in use')
  sys.exit()

try:
  # Listen on the server socket
  # ~~~~ INSERT CODE ~~~~
  #Temporarily 3 in queues? need to double-check 
  #Code for listening for client connections
  Server_Socket.listen(3)
  # ~~~~ END CODE INSERT ~~~~
  print ('Listening to socket')
except:
  print ('Failed to listen')
  sys.exit()

# RFC Section 13: caching in HTTP conditions 
# checking if it is a no-store or no-cache
def should_cache(response_bytes):
  headers = response_bytes.split(b'\r\n\r\n')[0].decode('utf-8')

  # MUST NOT cache if no-store is present
  if re.search(r'Cache-Control:.*?no-store', headers, re.IGNORECASE):
      return False
  
  # MUST NOT cache private responses in a shared cache (proxy)
  if re.search(r'Cache-Control:.*?private', headers, re.IGNORECASE):
        return False
  return True

# continuously accept connections
while True:
  print ('Waiting for connection...')
  clientSocket = None

  # Accept connection from client and store in the clientSocket
  try:
    # ~~~~ INSERT CODE ~~~~
    #code to accept client connection 
    clientSocket, addr = Server_Socket.accept()
    # ~~~~ END CODE INSERT ~~~~
    print ('Received a connection')
  except:
    print ('Failed to accept connection')
    sys.exit()

  # Get HTTP request from client
  # and store it in the variable: message_bytes
  # sally: Step 1.1: Where the proxy receives and parses the HTTP request from the client
  # ~~~~ INSERT CODE ~~~~
  # Code to recieve clients' requests and store it in message_bytes
  message_bytes = clientSocket.recv(BUFFER_SIZE)
  # ~~~~ END CODE INSERT ~~~~
  message = message_bytes.decode('utf-8')
  print ('Received request:')
  print ('< ' + message)

  # Extract the method, URI and version of the HTTP client request 
  requestParts = message.split()
  method = requestParts[0]
  URI = requestParts[1]
  version = requestParts[2]

  print ('Method:\t\t' + method)
  print ('URI:\t\t' + URI)
  print ('Version:\t' + version)
  print ('')

  # Get the requested resource from URI
  # Remove http protocol from the URI
  URI = re.sub('^(/?)http(s?)://', '', URI, count=1)

  # Remove parent directory changes - security
  URI = URI.replace('/..', '')

  # Split hostname from resource name
  #sally: Step 2.3: Host and port number that the proxy will be connected to
  resourceParts = URI.split('/', 1)
  hostname = resourceParts[0]
  resource = '/'

  if len(resourceParts) == 2:
    # Resource is absolute URI with hostname and resource
    resource = resource + resourceParts[1]

  print ('Requested Resource:\t' + resource)
  # Check if resource is in cache
  #sally: step 2.4: check if resource is in cache then fetch web object from here 
  try:
    cacheLocation = './' + hostname + resource
    if cacheLocation.endswith('/'):
        cacheLocation = cacheLocation + 'default'

    print ('Cache location:\t\t' + cacheLocation)

    fileExists = os.path.isfile(cacheLocation)
    
    # Check wether the file is currently in the cache
    cacheFile = open(cacheLocation, "r")
    cacheData = cacheFile.read()

    print ('Cache hit! Loading from cache file: ' + cacheLocation)
    # ProxyServer finds a cache hit
    # Send back response to client 
    #sally: step 1.2: Sending the repsonse back to client (if cache HIT)
    # ~~~~ INSERT CODE ~~~~
    #Code to send the cacheDAta to client
    #encode text back to bytes 
    clientSocket.sendall(cacheData.encode('utf-8')) 
    # ~~~~ END CODE INSERT ~~~~
    cacheFile.close()
    print ('Sent to the client:')
    print ('> ' + cacheData)
  except:
    # cache miss.  Get resource from origin server
    print('Cache miss: File not found in cache')
    originServerSocket = None
    # Create a socket to connect to origin server
    # and store in originServerSocket
    # sally: step 2.4: Cache miss, fetches web object from origin server 
    # ~~~~ INSERT CODE ~~~~
    #Step 7. create original server connection. 
    #https://docs.python.org/2.7/library/socket.html
    originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # ~~~~ END CODE INSERT ~~~~

    print ('Connecting to:\t\t' + hostname + '\n')
    try:
      # Get the IP address for a hostname
      address = socket.gethostbyname(hostname)
      # Connect to the origin server
      # ~~~~ INSERT CODE ~~~~
      # Get port number from original server by splitting the hostname 
      # RFC: 3.2.3 URI comparison
      if ':' in hostname:
        hostname_parts = hostname.split(':')
        hostname = hostname_parts[0]
        port = int(hostname_parts[1])
      else:
    # Default to port 80 for HTTP if not specified
        port = 80
        
      originServerSocket.connect((address, port))
      
      # ~~~~ END CODE INSERT ~~~~
      print ('Connected to origin Server')

      originServerRequest = ''
      originServerRequestHeader = ''
      # Create origin server request line and headers to send
      # and store in originServerRequestHeader and originServerRequest
      # originServerRequest is the first line in the request and
      # originServerRequestHeader is the second line in the request
      # ~~~~ INSERT CODE ~~~~
      # RFC 5.1 Request Line
      originServerRequest = f"{method} {resource} HTTP/1.1"
      originServerRequestHeader = f"Host: {hostname}\r\nConnection: close"
      # ~~~~ END CODE INSERT ~~~~

      # Construct the request to send to the origin server
      request = originServerRequest + '\r\n' + originServerRequestHeader + '\r\n\r\n'

      # Request the web resource from origin server
      print ('Forwarding request to origin server:')
      for line in request.split('\r\n'):
        print ('> ' + line)

      try:
        originServerSocket.sendall(request.encode())
      except socket.error:
        print ('Forward request to origin failed')
        sys.exit()

      print('Request sent to origin server\n')

      # Get the response from the origin server
      # ~~~~ INSERT CODE ~~~~
      #response in byte string 
      origin_server_response = b""
      while True:
      #each chunk received from original server is appended onto original_server_response to send to clients 
            origin_data = originServerSocket.recv(BUFFER_SIZE)
            if not origin_data:
              break
            origin_server_response += origin_data
      # ~~~~ END CODE INSERT ~~~~

      # Send the response to the client
      #sally: step 1.2: Sending the repsonse back to client (if cache MISS)
      #sally: step 1.3: modify to differentiate from proxy server resposne 
      # ~~~~ INSERT CODE ~~~~
      clientSocket.sendall(origin_server_response)
      # ~~~~ END CODE INSERT ~~~~

      # Create a new file in the cache for the requested file.
      if should_cache(origin_server_response):
        cacheDir, file = os.path.split(cacheLocation)
        print ('cached directory ' + cacheDir)
        if not os.path.exists(cacheDir):
          os.makedirs(cacheDir)
        cacheFile = open(cacheLocation, 'wb')

      # Save origin server response in the cache file
      # ~~~~ INSERT CODE ~~~~
        cacheFile.write(origin_server_response) 
      # ~~~~ END CODE INSERT ~~~~
        cacheFile.close()
        print ('cache file closed')

      # finished communicating with origin server - shutdown socket writes
      print ('origin response received. Closing sockets')
      originServerSocket.close()
       
      clientSocket.shutdown(socket.SHUT_WR)
      print ('client socket shutdown for writing')
    except OSError as err:
      print ('origin server request failed. ' + err.strerror)

  try:
    clientSocket.close()
  except:
    print ('Failed to close client socket')