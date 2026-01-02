from app import app
from vercel_wsgi import wsgi_app

handler = wsgi_app(app)