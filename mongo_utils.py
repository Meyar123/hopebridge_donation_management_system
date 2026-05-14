from mongoengine import connect, disconnect
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def connect_to_mongodb():
    """Connect to MongoDB using settings from Django configuration"""
    try:
        # Try using connection string first (for Railway)
        if hasattr(settings, 'MONGODB_URI') and settings.MONGODB_URI:
            # Log the URI for debugging (but mask sensitive parts)
            masked_uri = settings.MONGODB_URI
            if '@' in masked_uri:
                # Mask password in URI for logging
                parts = masked_uri.split('@')
                if len(parts) == 2:
                    user_pass = parts[0].split('://')[-1]
                    if ':' in user_pass:
                        user, _ = user_pass.split(':', 1)
                        masked_uri = masked_uri.replace(user_pass, f"{user}:***")
            
            # Check if the URI contains railway.internal which might not be accessible
            if 'railway.internal' in settings.MONGODB_URI:
                logger.warning("Railway internal MongoDB URI detected, this might not be accessible")
                # Try to construct a working URI using environment variables
                if hasattr(settings, 'MONGODB_HOST') and settings.MONGODB_HOST != 'localhost':
                    # Use the external hostname and port instead
                    external_uri = settings.MONGODB_URI.replace('mongodb.railway.internal', settings.MONGODB_HOST)
                    # Also replace the port if it's different
                    if hasattr(settings, 'MONGODB_PORT') and settings.MONGODB_PORT != 27017:
                        external_uri = external_uri.replace(':27017', f':{settings.MONGODB_PORT}')
                    
                    # Log the external URI instead of the internal one
                    external_masked_uri = external_uri
                    if '@' in external_masked_uri:
                        # Mask password in external URI for logging
                        parts = external_masked_uri.split('@')
                        if len(parts) == 2:
                            user_pass = parts[0].split('://')[-1]
                            if ':' in user_pass:
                                user, _ = user_pass.split(':', 1)
                                external_masked_uri = external_masked_uri.replace(user_pass, f"{user}:***")
                    
                    logger.info(f"Attempting to connect to MongoDB using external URI: {external_masked_uri}")
                    connect(host=external_uri, alias='default')
                else:
                    logger.info(f"Attempting to connect to MongoDB using URI: {masked_uri}")
                    connect(host=settings.MONGODB_URI, alias='default')
            else:
                logger.info(f"Attempting to connect to MongoDB using URI: {masked_uri}")
                connect(host=settings.MONGODB_URI, alias='default')
            logger.info(f"Successfully connected to MongoDB using URI")
            return True
        
        # Fallback to individual parameters
        logger.info(f"Falling back to individual MongoDB parameters")
        connection_params = {
            'db': settings.MONGODB_DATABASE,
            'host': settings.MONGODB_HOST,
            'port': settings.MONGODB_PORT,
            'alias': 'default'
        }
        
        # Add authentication if credentials are available
        if hasattr(settings, 'MONGODB_USER') and settings.MONGODB_USER:
            connection_params['username'] = settings.MONGODB_USER
        if hasattr(settings, 'MONGODB_PASSWORD') and settings.MONGODB_PASSWORD:
            connection_params['password'] = settings.MONGODB_PASSWORD
            
        logger.info(f"Connecting to MongoDB: {settings.MONGODB_HOST}:{settings.MONGODB_PORT}/{settings.MONGODB_DATABASE}")
        connect(**connection_params)
        logger.info(f"Successfully connected to MongoDB: {settings.MONGODB_DATABASE}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        logger.error(f"MongoDB settings - URI: {getattr(settings, 'MONGODB_URI', 'Not set')}")
        logger.error(f"MongoDB settings - Host: {getattr(settings, 'MONGODB_HOST', 'Not set')}")
        logger.error(f"MongoDB settings - Port: {getattr(settings, 'MONGODB_PORT', 'Not set')}")
        logger.error(f"MongoDB settings - Database: {getattr(settings, 'MONGODB_DATABASE', 'Not set')}")
        
        # If MongoDB connection fails, we'll continue without it
        # The application should still work for basic functionality
        logger.warning("MongoDB connection failed, continuing without MongoDB support")
        return False

# Global connection flag to avoid multiple connections
_mongodb_connected = False

def ensure_mongodb_connection():
    """Ensure MongoDB is connected, only connect once"""
    global _mongodb_connected
    if not _mongodb_connected:
        _mongodb_connected = connect_to_mongodb()
    return _mongodb_connected

def disconnect_from_mongodb():
    """Disconnect from MongoDB"""
    try:
        disconnect()
        logger.info("Disconnected from MongoDB")
        return True
    except Exception as e:
        logger.error(f"Failed to disconnect from MongoDB: {e}")
        return False

def get_mongodb_connection():
    """Get MongoDB connection status"""
    try:
        from mongoengine import get_connection
        connection = get_connection()
        return connection is not None
    except:
        return False
