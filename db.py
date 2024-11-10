from pymongo import MongoClient
from config import Config 

mongo = MongoClient()

def init_db():
    db = mongo['meta-hack']
    return db