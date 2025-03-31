from http.server import HTTPServer, BaseHTTPRequestHandler
import time
from datetime import datetime, timedelta
import email.utils

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        
        # Test case 1: Expires in the past
        if self.path == "/expired":
            past_time = datetime.now() - timedelta(days=1)
            expires = email.utils.formatdate(
                time.mktime(past_time.timetuple()), 
                localtime=False, 
                usegmt=True
            )
            self.send_header("Expires", expires)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"This content has already expired")
            
        # Test case 2: Expires in the future
        elif self.path == "/fresh":
            future_time = datetime.now() + timedelta(minutes=30)
            expires = email.utils.formatdate(
                time.mktime(future_time.timetuple()), 
                localtime=False, 
                usegmt=True
            )
            self.send_header("Expires", expires)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"This content is fresh for 30 minutes")
            
        # Default case
        else:
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Default response with no Expires header")

httpd = HTTPServer(('localhost', 8000), TestHandler)
print("Test server running on port 8000")
httpd.serve_forever()