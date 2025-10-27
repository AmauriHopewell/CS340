# Example Python Code to Insert a Document 

from pymongo import MongoClient 
from bson.objectid import ObjectId 
from pymongo.errors import PyMongoError #added to allow try/catch
import logging


import logging #added for easier debug with Jupyter
#explanation for different levels given here: https://stackoverflow.com/questions/27187930/how-to-use-logging-library-implement-logging-in-python
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnimalShelter(object): 
    """ CRUD operations for Animal collection in MongoDB """ 

    def __init__(self, USER='aacuser', PASS='amaurispassword'): 
        # Initializing the MongoClient. This helps to access the MongoDB 
        # databases and collections. This is hard-wired to use the aac 
        # database, the animals collection, and the aac user. 
        # 
        # You must edit the password below for your environment. 
        # 
        # Connection Variables 
        # 
        #USER = 'aacuser'
        #PASS = 'amaurispassword' #'SNHU1234' 
        HOST = 'localhost' 
        PORT = 27017 
        DB = 'aac' 
        COL = 'animals' 
        # 
        # Initialize Connection 
        # 
        try:
            self.client = MongoClient('mongodb://%s:%s@%s:%d' % (USER,PASS,HOST,PORT)) 
            self.database = self.client['%s' % (DB)] 
            self.collection = self.database['%s' % (COL)] 
            
            # Test the connection by listing databases (optional, for verification)
            #(This is why the try catch block is necessary)
            self.client.admin.command('ismaster')
            logger.info("Successfully connected to MongoDB as %s", USER)
        except PyMongoError as e:
            logger.error("Failed to connect to MongoDB: %s", e)
            raise

    # Create a method to return the next available record number for use in the create method
            
    # Complete this create method to implement the C in CRUD. 
    def create(self, data):
        if data is not None:  
            try: 
                result = self.database.animals.insert_one(data)  # data should be dictionary; modified to store in variable
                if result.acknowledged and result.inserted_id: #verify acknowledgement
                    logger.info("Successfully inserted document with ID: %s", result.inserted_id)
                    return True
                else: #catch possible error even if data is dictionary
                    logger.error("Insert operation not acknowledged")
                    return False
            except PyMongoError as e: 
                logger.error("Error during insert: %s", e)
                return False
        else: 
            raise Exception("Nothing to save, because data parameter is empty, error: %s", e) #modify slightly to show what error specifically is 

    # Create method to implement the R in CRUD.
    def read(self, lookup):
        """
        Queries for documents from the 'animals' collection using the provided lookup criteria.
        Uses MongoDB aggregation to retrieve multiple documents, with deduplication on 'animal_id'.
        
        Args:
            lookup (dict): Key/value lookup pair for the query (e.g., {'breed': 'Domestic Shorthair'}).
                           Empty dict {} returns all documents.
        
        Returns:
            list: List of unique matching documents (as dicts) if successful, empty list [] otherwise.
        
        Raises:
            None: Errors are logged, but method returns empty list on failure for graceful handling.
        
        Note:
            Uses aggregation to match, group by 'animal_id' for deduplication, and return unique docs.
        """
        if lookup is None or not isinstance(lookup, dict):
            logger.warning("Invalid lookup provided: must be a dict")
            return []
        
        try:
            # Aggregation pipeline for matching and deduplicating on 'animal_id'
            pipeline = [
                {"$match": lookup},  # Apply the filter
                {"$group": {  # Group by 'animal_id' to dedup
                    "_id": "$animal_id",  # Dedup key
                    "doc": {"$first": "$$ROOT"}  # Keep first occurrence
                }},
                {"$replaceRoot": {"newRoot": "$doc"}}  # Unwind back to documents
            ]
            cursor = self.collection.aggregate(pipeline)
            results = list(cursor)  # Convert to list of dicts
            logger.info("Retrieved %d unique documents matching criteria", len(results))
            return results
        except PyMongoError as e:
            logger.error("Error during query: %s", e)
            return []
    
    def update(self, lookup, update_data, many=True):
        """
        Updates document(s) in the 'animals' collection matching the lookup criteria.
        
        Args:
            lookup (dict): Key/value lookup pair to find documents to update.
            update_data (dict): Key/value pairs for the update (e.g., {'$set': {'outcome_type': 'Updated'}}).
                                Must be acceptable to update_one() or update_many().
            many (bool): If True (default), updates all matching documents; if False, updates only one.
        
        Returns:
            int: The number of documents modified (0 if none or error).
        
        Raises:
            None: Errors are logged, but method returns 0 on failure.
        """
        if lookup is None or not isinstance(lookup, dict) or not lookup:
            logger.warning("Invalid lookup for update: must be a non-empty dict")
            return 0
        
        if update_data is None or not isinstance(update_data, dict) or not update_data:
            logger.warning("Invalid update_data: must be a non-empty dict")
            return 0
        
        try:
            if many:
                result = self.collection.update_many(lookup, update_data)
            else:
                result = self.collection.update_one(lookup, update_data)
            
            if result.acknowledged:
                logger.info("Successfully updated %d documents", result.modified_count)
                return result.modified_count
            else:
                logger.error("Update operation not acknowledged")
                return 0
        except PyMongoError as e:
            logger.error("Error during update: %s", e)
            return 0

    def delete(self, lookup, many=True):
        """
        Deletes document(s) from the 'animals' collection matching the lookup criteria.
        
        Args:
            lookup (dict): Key/value lookup pair to find documents to delete.
            many (bool): If True (default), deletes all matching documents; if False, deletes only one.
        
        Returns:
            int: The number of documents deleted (0 if none or error).
        
        Raises:
            None: Errors are logged, but method returns 0 on failure.
        """
        if lookup is None or not isinstance(lookup, dict) or not lookup:
            logger.warning("Invalid lookup for delete: must be a non-empty dict")
            return 0
        
        try:
            if many:
                result = self.collection.delete_many(lookup)
            else:
                result = self.collection.delete_one(lookup)
            
            if result.acknowledged:
                logger.info("Successfully deleted %d documents", result.deleted_count)
                return result.deleted_count
            else:
                logger.error("Delete operation not acknowledged")
                return 0
        except PyMongoError as e:
            logger.error("Error during delete: %s", e)
            return 0
    
    def __del__(self): # add function to close connection based on stackoverflow recommendations
        """
        Closes the MongoDB client connection when the object is destroyed.
        """
        try:
            print("trying to close client")
            if self.client:
                self.client.close()
            else:
                print("no client to close")
        except PyMongoError as e:
            logger.error("Error during delete: %s", e)