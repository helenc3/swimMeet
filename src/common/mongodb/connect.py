"""
MongoDB Helper Script for connecting to MongoDB

"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv
from common.utils import DB_NAME


### connection functions
# load environment variables from .env file -- necessary if you store your mongodb uri in a .env file
load_dotenv()

## get mongodb uri from environment variables 
MONGODB_URI = os.getenv("MONGODB_URI")

if not MONGODB_URI:
    raise ValueError(
        "MONGODB_URI not found in environment variables. "
        "Please create a .env file with your MongoDB connection string. "
        "See .env.example for template."
    )

def connect_to_mongodb():
    """connect to MongoDB and return the database"""
    try:
        client = MongoClient(MONGODB_URI)
        db = client[DB_NAME]
        print(f"Connected to MongoDB! Database: {DB_NAME}")
        return client, db
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        print("\nMake sure you:")
        print("1. installed pymongo: pip install pymongo")
        print("2. have the correct connection string")
        print("3. are connected to the internet (if using Atlas)")
        return None, None
