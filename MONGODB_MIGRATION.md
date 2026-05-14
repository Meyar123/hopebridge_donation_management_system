# MongoDB Migration Guide

This guide explains how to migrate your Django donation management system from SQLite to MongoDB.

## Prerequisites

1. **Install MongoDB**: Download and install MongoDB Community Server from [mongodb.com](https://www.mongodb.com/try/download/community)
2. **Start MongoDB Service**: Ensure MongoDB is running on `localhost:27017`

## Installation

1. **Install Python packages**:
   ```bash
   pip install mongoengine pymongo
   ```

2. **Verify installation**:
   ```bash
   python check_mongodb.py
   ```

## Migration Process

### Step 1: Test MongoDB Connection
```bash
python check_mongodb.py
```

### Step 2: Migrate Data from SQLite to MongoDB
```bash
python migrate_to_mongodb.py
```

**Options:**
- `--dry-run`: Preview what will be migrated without actually migrating data
- Example: `python migrate_to_mongodb.py --dry-run`

### Step 3: Verify Migration
After migration, check that data was transferred correctly:
```bash
python check_mongodb.py
```

## Current System Status

**This system is already using MongoDB!** The migration command is provided for reference, but the application is currently running on MongoDB with the following setup:

- **Database**: `donation_management_db`
- **Host**: `localhost:27017`
- **Models**: All using MongoDB document models
- **Views**: Using `mongodb_only_views.py`

## File Structure

- `mongo_models.py` - MongoDB document models using MongoEngine
- `mongo_utils.py` - MongoDB connection utilities
- `mongodb_only_views.py` - MongoDB-based views
- `migrate_to_mongodb.py` - Data migration script
- `check_mongodb.py` - MongoDB connection test

## MongoDB Collections

The system uses the following collections:
- `users` - User accounts and profiles
- `donors` - Donor profiles
- `recipients` - Recipient profiles  
- `volunteers` - Volunteer profiles
- `items` - Donated items
- `donations` - Donation records
- `activities` - Volunteer activities
- `volunteer_activities` - Activity participation

## Key Differences

### Models
- **SQLite**: Django ORM models with foreign keys
- **MongoDB**: Document models with embedded documents and references

### Queries
- **SQLite**: `Item.objects.filter(category='books')`
- **MongoDB**: `MongoItem.objects(category='books')`

### Relationships
- **SQLite**: Foreign key relationships
- **MongoDB**: ObjectId references and embedded documents

## Usage Examples

### Creating a User
```python
from mongo_models import MongoUser, Address

address = Address(
    street="123 Main St",
    city="New York",
    postal_code="10001",
    country="USA"
)

user = MongoUser(
    email="user@example.com",
    name="John Doe",
    phone="123-456-7890",
    address=address
)
user.save()
```

### Querying Items
```python
from mongo_models import MongoItem

# Find all books
books = MongoItem.objects(category='books')

# Search by name
search_results = MongoItem.objects(name__icontains='laptop')
```

## Benefits of MongoDB

1. **Flexible Schema**: Easy to add new fields without migrations
2. **Embedded Documents**: Store related data together (e.g., address in user)
3. **Horizontal Scaling**: Better performance for large datasets
4. **JSON-like Structure**: Natural fit for web applications

## Troubleshooting

### Connection Issues
- Ensure MongoDB is running: `mongod --version`
- Check connection string in settings
- Verify firewall settings

### Migration Issues
- Check data integrity before migration
- Backup SQLite database first
- Review migration logs for errors

### Performance Issues
- Add database indexes for frequently queried fields
- Use MongoDB Compass for query optimization
- Monitor database performance

## Next Steps

1. Test the migration with a small dataset first
2. Update your views to use MongoDB models
3. Implement proper error handling
4. Add database indexes for performance
5. Set up MongoDB monitoring and backups

## Support

For issues with the migration:
1. Check MongoDB logs
2. Verify Python package versions
3. Test with the provided test script
4. Review the migration logs
