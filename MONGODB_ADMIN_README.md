# MongoDB Admin System

This document describes the MongoDB-based admin system that replaces the Django ORM admin for the Donation Management System.

## Overview

The MongoDB Admin system provides a complete administrative interface for managing users, donations, and activities using MongoDB as the primary database. It includes:

- **User Management**: View, edit, block/unblock, and delete users
- **Donation Management**: Monitor donations, update statuses, and manage items
- **Activity Management**: Oversee volunteer activities and participants
- **Dashboard**: Comprehensive statistics and analytics
- **Activity Logs**: Track system activity and user actions

## Features

### 🔐 Authentication
- MongoDB-based user authentication
- Admin role verification (is_staff or is_superuser)
- Session management for admin users

### 📊 Dashboard
- Real-time statistics for users, donations, and activities
- Interactive charts and graphs
- Recent activity monitoring
- Category-based analytics
- Export functionality

### 👥 User Management
- View all users with role information
- Search and filter users
- Block/unblock user accounts
- Delete users and related data
- Detailed user profiles with activity history

### 🎁 Donation Management
- Monitor all donations and their status
- Filter by status, category, and search terms
- Update donation statuses (available/claimed/shipped)
- Delete donations and associated items
- View donor and recipient information

### 🤝 Activity Management
- Manage volunteer activities
- View organizer information
- Filter by category and search terms
- Delete activities and related data

### 📋 Activity Logs
- Track system activity
- Monitor user actions
- View donation and activity events

## File Structure

```
├── mongodb_admin.py          # Main admin views and logic
├── templates/admin/          # Admin templates
│   ├── admin_dashboard.html  # Main dashboard
│   ├── user_management.html  # User management interface
│   ├── user_detail.html      # Individual user details
│   ├── donation_management.html # Donation management
│   ├── activity_management.html # Activity management
│   └── activity_logs.html    # Activity logs
├── test_mongodb_admin.py     # Test script
└── MONGODB_ADMIN_README.md   # This file
```

## URL Routes

The admin system uses the following URL patterns:

- `/admin-dashboard/` - Main admin dashboard
- `/admin-users/` - User management
- `/admin-users/<user_id>/` - User detail view
- `/admin-users/<user_id>/toggle-status/` - Toggle user status
- `/admin-users/<user_id>/delete/` - Delete user
- `/admin-donations/` - Donation management
- `/admin-donations/<donation_id>/ship/` - Mark donation as shipped
- `/admin-donations/<donation_id>/delete/` - Delete donation
- `/admin-activities/` - Activity management
- `/admin-activities/<activity_id>/delete/` - Delete activity
- `/admin-logs/` - Activity logs
- `/admin-export/` - Export data

## Usage

### Accessing the Admin Panel

1. **Login as Admin**: Users must have `is_staff=True` or `is_superuser=True` in MongoDB
2. **Navigate to Admin**: Go to `/admin-dashboard/` after login
3. **Use Navigation**: Use the top navigation to access different admin sections

### Creating Admin Users

To create an admin user, you can use the Django shell or create a management command:

```python
from mongo_models import User as MongoUser
from django.contrib.auth.hashers import make_password

# Create admin user
admin_user = MongoUser(
    email='admin@example.com',
    name='Admin User',
    phone='1234567890',
    password_hash=make_password('admin123'),
    is_active=True,
    is_staff=True,
    is_superuser=True,
    date_joined=datetime.utcnow()
)
admin_user.save()
```

### Key Functions

#### `mongo_admin_dashboard(request)`
- Displays comprehensive statistics
- Shows recent activity
- Provides charts and analytics
- Supports time period filtering

#### `mongo_admin_user_management(request)`
- Lists all users with role information
- Supports search and filtering
- Provides user management actions

#### `mongo_admin_donation_management(request)`
- Manages donations and items
- Supports status updates
- Provides filtering and search

#### `mongo_admin_activity_management(request)`
- Manages volunteer activities
- Shows organizer information
- Supports filtering by category

## Data Relationships

The admin system handles complex MongoDB relationships:

### Users and Roles
- Users can have multiple roles (donor, recipient, volunteer)
- Roles are stored in separate collections with user_id references
- Admin queries join data across collections

### Donations and Items
- Donations reference items by item_id
- Items reference donors by donor_id
- Admin queries resolve these relationships for display

### Activities and Volunteers
- Activities reference volunteers by volunteer_id
- Volunteers reference users by user_id
- Admin queries show organizer information

## Security

### Authentication
- All admin views require authentication
- Users must have admin privileges (is_staff or is_superuser)
- Session-based authentication

### Authorization
- Admin decorator checks user permissions
- Redirects unauthorized users
- Protects against unauthorized access

### Data Protection
- Confirmation dialogs for destructive actions
- Soft deletes where appropriate
- Audit trail for admin actions

## Testing

Run the test script to verify the admin system:

```bash
python test_mongodb_admin.py
```

The test script checks:
- MongoDB connection
- Data queries
- Relationship resolution
- Statistics calculations

## Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**
   - Check MongoDB is running
   - Verify connection settings in settings.py
   - Ensure database exists

2. **Admin Access Denied**
   - Verify user has is_staff=True or is_superuser=True
   - Check user is active (is_active=True)
   - Clear browser session if needed

3. **Missing Data in Admin**
   - Check MongoDB collections exist
   - Verify data relationships
   - Run migration scripts if needed

4. **Template Errors**
   - Check template syntax
   - Verify context variables
   - Check for missing template tags

### Debug Mode

Enable debug mode in settings.py for detailed error messages:

```python
DEBUG = True
```

## Performance Considerations

### Database Optimization
- Use MongoDB indexes for frequently queried fields
- Implement pagination for large datasets
- Cache frequently accessed data

### Query Optimization
- Use projection to limit returned fields
- Implement efficient relationship queries
- Consider aggregation pipelines for complex statistics

## Future Enhancements

- **Real-time Updates**: WebSocket integration for live data
- **Advanced Analytics**: More detailed reporting and charts
- **Bulk Operations**: Mass user/donation management
- **Audit Trail**: Detailed logging of admin actions
- **API Integration**: REST API for admin operations
- **Mobile Support**: Responsive design improvements

## Support

For issues or questions about the MongoDB Admin system:

1. Check this documentation
2. Run the test script
3. Check Django logs for errors
4. Verify MongoDB connection and data

## Migration from Django ORM Admin

The MongoDB Admin system is designed to replace the Django ORM admin. Key differences:

- **Database**: Uses MongoDB instead of SQLite/PostgreSQL
- **Queries**: Uses MongoDB queries instead of Django ORM
- **Relationships**: Manual relationship resolution instead of ORM joins
- **Templates**: Custom templates instead of Django admin templates
- **Authentication**: MongoDB-based instead of Django auth

The system maintains the same functionality while providing better performance and scalability with MongoDB.
