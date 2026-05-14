# Donation Management System

A comprehensive Django-based web application for managing donations between donors and recipients, featuring user authentication, location-based services, and an intuitive admin interface.

## 🚀 Features

### Core Functionality

- **User Management**: Complete user registration, authentication, and profile management
- **Donation System**: Create, update, and manage donation items with detailed information
- **Location Services**: GPS coordinates and address management for donation items
- **Role-Based Access**: Separate dashboards for donors and recipients
- **Admin Dashboard**: Comprehensive administrative interface for system management

### User Types

- **Donors**: Can create and manage donation listings
- **Recipients**: Can browse and request available donations
- **Administrators**: Full system access and user management capabilities

### Technical Features

- **Django 5.2.3**: Latest Django framework with modern Python support
- **SQLite Database**: Lightweight database for development and small-scale deployment
- **Responsive Design**: Mobile-friendly templates and UI components
- **Location Integration**: Latitude/longitude coordinates for donation items
- **Address Management**: Comprehensive address fields with city, apartment, and postal code support

## 🏗️ Project Structure

```text
final_corrected_donation_project/
├── admin.py                 # Main admin configuration
├── apps.py                  # Main app configuration
├── core/                    # Core utilities and results
│   ├── result_utils.py
│   └── results.py
├── donations/               # Donation management app
│   ├── models.py            # Donation and item models
│   ├── views.py             # Donation-related views
│   ├── admin.py             # Donation admin interface
│   └── migrations/          # Database migrations
├── users/                   # User management app
│   ├── models.py            # User model and extensions
│   ├── views.py             # User authentication views
│   ├── admin.py             # User admin interface
│   └── migrations/          # User-related migrations
├── mixins/                  # Reusable model mixins
│   ├── address_mixin.py     # Address field mixin
│   └── cancelable_mixin.py  # Cancellation functionality
├── utils/                   # Utility functions
│   └── location_utils.py    # Location-related utilities
├── templates/               # HTML templates
│   ├── admin/               # Admin interface templates
│   ├── dashboard/           # User dashboard templates
│   ├── donations/           # Donation management templates
│   └── registration/        # Authentication templates
├── static/                  # Static files (CSS, JS, images)
├── manage.py                # Django management script
├── settings.py              # Django settings configuration
├── urls.py                  # Main URL routing
└── requirements.txt         # Python dependencies
```

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.13.5 or higher
- pip (Python package installer)

### Installation Steps

1. **Clone the repository**

```bash
git clone [your-repository-url]
cd final_corrected_donation_project
```

2. **Install dependencies**

```bash
py -m pip install -r requirements.txt
```

3. **Run database migrations**

```bash
py manage.py migrate
```

4. **Create a superuser (optional)**

```bash
py manage.py createsuperuser
```

5. **Start the development server**

```bash
py manage.py runserver
```

6. **Access the application**

- Main application: http://127.0.0.1:8000/
- Admin interface: http://127.0.0.1:8000/admin/

## 📱 Usage

### For Donors

1. Register an account and select "Become a Donor"
2. Access the donor dashboard
3. Create new donation listings with item details and location
4. Manage existing donations

### For Recipients

1. Register an account and select "Become a Recipient"
2. Browse available donations
3. Request items of interest
4. Manage donation requests

### For Administrators

1. Access the admin dashboard at `/admin/`
2. Manage users, donations, and system settings
3. Monitor system activity and user interactions

## 🔧 Configuration

### Database

- Default: SQLite (development)
- Production: Can be configured for MySQL/PostgreSQL

### Location Services

- GPS coordinates are automatically captured
- Address fields support international formats
- Location utilities for distance calculations

### Security

- User authentication and authorization
- Role-based access control
- Secure password handling

## 🚀 Deployment

### Development

- Use the built-in Django development server
- Suitable for testing and development

### Production

- Use a production WSGI server (Gunicorn, uWSGI)
- Configure a production database (MySQL/PostgreSQL)
- Set up proper static file serving
- Configure environment variables for sensitive data

## 📊 Dependencies

- **Django**: Web framework (>=4.0)
- **mysqlclient**: MySQL database adapter (for production use)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is developed for educational purposes as part of an Information Systems Management course project.

## 👥 Team

Developed as a final project for the Information Systems Management program, Year 3.

## 📞 Support

For technical support or questions about the project, please refer to the project documentation or contact the development team.

---

**Note**: This is a development version. For production use, additional security measures and configuration changes are required.

# Trigger redeploy
