from pymongo import MongoClient
from datetime import datetime

# Create a MongoClient and select your database
client = MongoClient("mongodb://localhost:27017/")
db = client["database"]  # Use your database name here
commit_history = db["commit_history"]  # Your collection



def insert_database(event_type, commit_id, author, from_branch, to_branch, timestamp=None):
    """
    Insert a document into the MongoDB database with the provided arguments.
    """
    if not timestamp:
        timestamp = datetime.utcnow()
    document = {        
        "request_id": commit_id,
        "author": author, 
        "action": event_type,
        "from_branch": from_branch,
        "to_branch": to_branch,
        "timestamp": timestamp
    }
    try:
        insert_result = commit_history.insert_one(document)
        return {
            "message": "Document inserted successfully",
            "document_id": str(insert_result.inserted_id)
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_database(start_row, stop_row):
    """
    Fetch commit history from the database between the start and stop rows, sorted by timestamp in descending order.
    
    Args:
        start_row (int): The row number to start fetching data from (inclusive).
        stop_row (int): The row number to stop fetching data at (inclusive).
        
    Returns:
        list: List of commit history records within the specified range, sorted by timestamp in descending order.
    """
    try:
        # Fetch data from the database with pagination (skip and limit)
        results = commit_history.find() \
            .sort("timestamp", -1)  # Sort by timestamp in descending order (most recent first)
        
        # Fetch the range from start_row to stop_row
        # skip() is used to skip the first start_row records
        # limit() is used to fetch the remaining rows from start_row to stop_row
        commit_records = list(results.skip(start_row).limit(stop_row - start_row))

        # Return the fetched documents
        return commit_records
    
    except Exception as e:
        return {"error": str(e)}

