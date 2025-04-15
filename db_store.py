from pymongo import MongoClient
import gridfs

client = None
db = None
fs = None

def init_db():
    global client, db, fs
    client = MongoClient('mongodb://localhost:27017/')
    db = client['facescan360']
    fs = gridfs.GridFS(db)

def get_auth_db():
    return db['users']

def get_reports_db():
    return db['reports']

def get_gridfs():
    return fs