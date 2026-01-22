from pathlib import Path
import os
from decouple import config
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    # 'rest_framework.authtoken',  # Changed from simplejwt
    'rest_framework_simplejwt', # Changed back to JWT
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    
    # Local apps
    'apps.accounts',
    'apps.staff',
    'apps.students',
    'apps.academic',
    'apps.grades',
    'apps.attendance',
    'apps.finance',
    'apps.timetable',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # 'rest_framework.authentication.TokenAuthentication',  # Changed from JWT
        # 'rest_framework.authentication.SessionAuthentication',  # For browsable API
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    
    'JTI_CLAIM': 'jti',
}

# CORS
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000').split(',')
CORS_ALLOW_CREDENTIALS = True

# CSRF
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost:8000').split(',')

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Session settings
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400  # 24 hours


# DRF Spectacular Settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'School Management System API',
    'DESCRIPTION': 'Comprehensive API for managing school operations including staff, students, academics, finance, and more',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    
    # Enum naming
    # 'ENUM_NAME_OVERRIDES': {
    #     # Student statuses
    #     'StudentStatusEnum': 'apps.students.models.Student.status',
    #     'EnrollmentStatusEnum': 'apps.academic.models.Enrollment.status',
        
    #     # Payment methods
    #     'PaymentMethodEnum': 'apps.finance.models.Payment.payment_method',
    #     'ExpenditurePaymentMethodEnum': 'apps.finance.models.Expenditure.payment_method',
    #     'SalaryPaymentMethodEnum': 'apps.staff.models.SalaryPayment.payment_method',
        
    #     # Terms
    #     'TermEnum': 'apps.grades.models.Grade.term',
    #     'InvoiceTermEnum': 'apps.finance.models.Invoice.term',
    #     'FeeStructureTermEnum': 'apps.finance.models.FeeStructure.term',
        
    #     # Staff
    #     'StaffTypeEnum': 'apps.staff.models.Staff.staff_type',
    #     'StaffAttendanceStatusEnum': 'apps.staff.models.StaffAttendance.status',
    #     'LeaveTypeEnum': 'apps.staff.models.LeaveRequest.leave_type',
    #     'LeaveStatusEnum': 'apps.staff.models.LeaveRequest.status',
        
    #     # Grades
    #     'GradeTypeEnum': 'apps.grades.models.Grade.grade_type',
        
    #     # Attendance
    #     'AttendanceStatusEnum': 'apps.attendance.models.Attendance.status',
        
    #     # User roles
    #     'UserRoleEnum': 'apps.accounts.models.User.role',
        
    #     # Gender
    #     'GenderEnum': 'apps.students.models.Student.gender',
    #     'StaffGenderEnum': 'apps.staff.models.Staff.gender',
    # },
    
    # Component split
    'COMPONENT_SPLIT_REQUEST': True,
    
    # Schema customization
    'SCHEMA_PATH_PREFIX': '/api/',
    'SCHEMA_PATH_PREFIX_TRIM': True,

    # Swagger UI settings
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'filter': True,  # Enable filter/search bar
        'tryItOutEnabled': True,
        'displayRequestDuration': True,
        'docExpansion': 'list',  # 'list', 'full', or 'none'
        'defaultModelsExpandDepth': 3,
        'defaultModelExpandDepth': 3,
        'defaultModelRendering': 'model',  # 'example' or 'model'
        'tagsSorter': 'alpha',  # Sort tags alphabetically
        'operationsSorter': 'alpha',  # Sort operations alphabetically
        'showExtensions': True,
        'showCommonExtensions': True,
    },

    # Authentication
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            # 'tokenAuth': {
            #     'type': 'apiKey',
            #     'in': 'header',
            #     'name': 'Authorization',
            #     'description': 'Token-based authentication with required prefix "Token"'
            # }
            'jwtAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': 'JWT Authentication using access token'
            }
        }
    },
    'SECURITY': [{'jwtAuth': []}],

    # Let drf-spectacular auto-generate enum names (they'll have hash suffixes but will work)
    'ENUM_GENERATE_CHOICE_DESCRIPTION': True,    

    # Tags - organize endpoints by category
    # 'TAGS': [
    #     {'name': 'Authentication', 'description': 'Login, logout, token management'},
    #     {'name': 'Users', 'description': 'User account management'},
    #     {'name': 'Staff', 'description': 'Staff management and HR operations'},
    #     {'name': 'Students', 'description': 'Student registration and management'},
    #     {'name': 'Parents', 'description': 'Parent/guardian information'},
    #     {'name': 'Academic', 'description': 'Academic years, classes, subjects'},
    #     {'name': 'Grades', 'description': 'Grade management and reports'},
    #     {'name': 'Attendance', 'description': 'Attendance tracking and reports'},
    #     {'name': 'Finance', 'description': 'Fee management, invoices, payments'},
    #     {'name': 'Timetable', 'description': 'Class schedules and syllabus'},
    #     {'name': 'System', 'description': 'Health checks and system info'},
    # ],
    
    # Preprocessing hook to add tags
    # 'PREPROCESSING_HOOKS': ['scripts.schema_hooks.preprocess_schema_tags'],
}