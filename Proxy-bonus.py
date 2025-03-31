# Include the libraries for socket and system calls
# sally: Identifying the interactions in step 1 and 2. 
import socket
import sys
import os
import argparse
import re
import time
import email.utils

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
  try: 
    #retrieve headers 
    headers = response_bytes.split(b'\r\n\r\n')[0].decode('utf-8')
    status_line = headers.split('\r\n')[0]
    print(f"HEADERS: {headers}")

    #checking for a 302 response - only cacheable if indicated by Cache-Control 
    if re.search(r'HTTP/\d\.\d\s+302', status_line, re.IGNORECASE):
      print('302 response detected')

      #check cache-control or expires
      has_cache_control = re.search(r'Cache-Control:', headers, re.IGNORECASE)
      has_expires = re.search(r'Expires:', headers, re.IGNORECASE)

      if not (has_cache_control or has_expires):
          print('no cache-directives, dont cache')
          return False #dont cache wihtout these headings 
    # MUST NOT cache if no-store is present
    if re.search(r'Cache-Control:.*?no-store', headers, re.IGNORECASE):
        return False
    
    # MUST NOT cache private responses in a shared cache (proxy)
    if re.search(r'Cache-Control:.*?private', headers, re.IGNORECASE):
        return False
    
    # Extract Expires header if present
    #############################################################################
    # BONUS MARK (1) Expires header of cached objects to determine 
    # if a new copy is needed from the origin server instead of just 
    # sending back the cached copy 
    #using the same method as extracting headers from other parts 
    is_expiry = re.search(r'Expires:\s*(.+?)(\r\n|\n)', headers, re.IGNORECASE)
    #group the expiry 
    expires_date_str = is_expiry.group(1).strip()
    expires_date = email.utils.parsedate(expires_date_str)

    #if there is expires date, compare
    if expires_date:
       #with time now 
       expires = time.mktime(expires_date)
       #chane datetime to time to match with expires timestamp 
       now = time.time()
       #if now is after expiry header
       if now > expires:
          print(f"Cache expired (Expires: {expires_date_str})")
            # Cache expired - fetch fresh copy
          raise Exception("Expiry header: Cache expired")
       else:
          print(f"Expiry header: (Expires: {expires_date_str})")

    else:
        print(f"Could not parse Expiry: {expires_date_str}")     
    #############################################################################

      # If 'no-cache' is present, cache but require revalidation
    if re.search(r'Cache-Control:.*?no-cache', headers, re.IGNORECASE):
        print("Response with no-cache directive, will revalidate")
        return True
    return True
  except Exception as e:
      print(f"Error in should_cache: {e}")
      return False
  
#Get validators for no-cache directives 
def validators(cacheData):
   validators = {}
   is_etag = re.search(r'ETag:\s*"([^"]+)"', cacheData, re.IGNORECASE)
   is_last_modified = re.search(r'Last-Modified:\s*(.+)', cacheData, re.IGNORECASE)
  #grouping etag 
   if is_etag:
      validators['etag'] = is_etag.group(1)
  #grouping last_modified 
   if is_last_modified:
      validators['last-modified'] = is_last_modified.group(1)

   return validators   

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
    cacheData = cacheFile.readlines()
    cacheData = ''.join(cacheData)

    print ('Cache hit! Loading from cache file: ' + cacheLocation)
    # ProxyServer finds a cache hit
    # Send back response to client 
    #sally: step 1.2: Sending the repsonse back to client (if cache HIT)
    # ~~~~ INSERT CODE ~~~~
    #Code to send the cacheDAta to client
        # Check if we need to revalidate based on cache directives
    should_revalidate = False
    #checking max_age 
    is_max_age = re.search(r'Cache-Control:.*?max-age=(\d+)', cacheData, re.IGNORECASE)
    # If max-age is found
    if is_max_age:
        max_age = int(is_max_age.group(1))
        try:
            #path to timestamp
            timestamp_file = cacheLocation + ".age"
            # Open and read the timestamp file
            with open(timestamp_file, "r") as tf:
                #read in cached time 
                cached_time = float(tf.read().strip())
             #get current time to measure agaisnt cache time   
            current_time = time.time()
            #calculate time until expired
            if current_time - cached_time > max_age:
                #print if expired
                print(f"Cache expired, max-age={max_age}")
                #raise exception to get new copy 
                raise Exception("Cache expired")
        except Exception as e:
            raise 
    # Check for must-revalidate directive
    if re.search(r'Cache-Control:.*?(must-revalidate|no-cache)', cacheData, re.IGNORECASE):
        print("Response requires revalidation, revalidating...")
        should_revalidate = True

    if should_revalidate:
        print("Revalidating with original server...")
        # Get validators from cached response
        cache_validators = validators(cacheData)

        #open socket to revalidate 
        revalidateSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            # Get the IP address for a hostname
            address = socket.gethostbyname(hostname)
            
            # Determine port
            if ':' in hostname:
                hostname_parts = hostname.split(':')
                hostname = hostname_parts[0]
                port = int(hostname_parts[1])
            else:
                port = 80
                
            # Connect to origin server
            revalidateSocket.connect((address, port))

            # Create conditional request headers based on available validators
            conditionalHeaders = ""
            if 'etag' in cache_validators:
                conditionalHeaders += f"If-None-Match: \"{cache_validators['etag']}\"\r\n"
            if 'last-modified' in cache_validators:
                conditionalHeaders += f"If-Modified-Since: {cache_validators['last-modified']}\r\n"

             # Create request
            revalidateRequest = f"{method} {resource} HTTP/1.1\r\n"
            revalidateRequestHeader = f"Host: {hostname}\r\nConnection: close\r\n{conditionalHeaders}"
            request = revalidateRequest + revalidateRequestHeader + "\r\n"
            
            print("Sending revalidation request to origin server:")
            for line in request.split('\r\n'):
                print('> ' + line)
                
            # Send revalidation request
            revalidateSocket.sendall(request.encode())
            
            # Get response
            revalidate_response = b""
            while True:
                revalidate_data = revalidateSocket.recv(BUFFER_SIZE)
                if not revalidate_data:
                    break
                revalidate_response += revalidate_data
            
             # Check if response is 304 Not Modified
            headers = revalidate_response.split(b'\r\n\r\n')[0].decode('utf-8')
            status_line = headers.split('\r\n')[0]

            if "304 Not Modified" in status_line:
                print("304 not modified, use cached version")
                clientSocket.sendall(cacheData.encode('utf-8'))
            else:
                print("Resource modified, using new version")
                # Update cache
                cacheFile = open(cacheLocation, 'wb')
                cacheFile.write(revalidate_response)
                cacheFile.close()
                
                # Save timestamp for max-age calculations
                timestamp_file = cacheLocation + ".age"
                with open(timestamp_file, "w") as tf:
                    tf.write(str(time.time()))
                    
                # Send new response to client
                clientSocket.sendall(revalidate_response)
                
            revalidateSocket.close()
        except OSError as err:
                print(f"Revalidation failed: {err.strerror}, falling back..")
                clientSocket.sendall(cacheData.encode('utf-8'))

    else:
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
      decide_caching = should_cache(origin_server_response)
      if decide_caching:
          cacheDir, file = os.path.split(cacheLocation)
          print('cached directory ' + cacheDir)
          if not os.path.exists(cacheDir):
              os.makedirs(cacheDir)
          cacheFile = open(cacheLocation, 'wb')

          # Save origin server response in the cache file
          # ~~~~ INSERT CODE ~~~~
          cacheFile.write(origin_server_response) 
          # Save timestamp for max-age calculations
          timestamp_file = cacheLocation + ".age"
          #open and check if response is still usable
          with open(timestamp_file, "w") as tf:
              tf.write(str(time.time()))
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
