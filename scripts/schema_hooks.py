"""
Schema preprocessing hooks for drf-spectacular
"""


def preprocess_schema_tags(endpoints):
    """
    Add proper tags to endpoints for better organization in Swagger UI
    """
    tag_mapping = {
        '/api/v1/auth/': 'Authentication',
        '/api/v1/users/': 'Users',
        '/api/v1/staff/': 'Staff',
        '/api/v1/salary': 'Staff',
        '/api/v1/staff-attendance/': 'Staff',
        '/api/v1/leave-requests/': 'Staff',
        '/api/v1/students/': 'Students',
        '/api/v1/parents/': 'Parents',
        '/api/v1/student-parents/': 'Parents',
        '/api/v1/academic-years/': 'Academic',
        '/api/v1/subjects/': 'Academic',
        '/api/v1/classes/': 'Academic',
        '/api/v1/enrollments/': 'Academic',
        '/api/v1/subject-assignments/': 'Academic',
        '/api/v1/grades/': 'Grades',
        '/api/v1/attendance/': 'Attendance',
        '/api/v1/fee-structures/': 'Finance',
        '/api/v1/invoices/': 'Finance',
        '/api/v1/payments/': 'Finance',
        '/api/v1/expenditures/': 'Finance',
        '/api/v1/financial-dashboard/': 'Finance',
        '/api/v1/timetable/': 'Timetable',
        '/api/v1/syllabus/': 'Timetable',
        '/health/': 'System',
    }
    
    for path, path_regex, method, callback in endpoints:
        # Find matching tag
        for path_prefix, tag in tag_mapping.items():
            if path.startswith(path_prefix):
                # Add tag to the callback
                if hasattr(callback, 'cls'):
                    if not hasattr(callback.cls, 'tags'):
                        callback.cls.tags = [tag]
                break
    
    return endpoints