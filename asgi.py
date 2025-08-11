from asgiref.wsgi import WsgiToAsgi
from wsgi import application
app = WsgiToAsgi(application)
