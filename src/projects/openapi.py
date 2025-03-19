from fastapi import status
from openapi import FILE_UPLOAD_RELATED_RESPONSES

PROJECT_CREATE_SCHEMA = {
    **FILE_UPLOAD_RELATED_RESPONSES,
    status.HTTP_400_BAD_REQUEST: {
        'description': 'Invalid JSON in project_data field or data string must be a valid JSON.',
        'content': {
            'application/json': {
                'examples': {
                    'invalid_project_data': {
                        'summary': 'Invalid JSON in project_data field',
                        'value': {
                            'detail': 'Invalid JSON in project_data field.',
                        }
                    },
                    'not_json_project_data': {
                        'summary': 'project_data string is not convertable to json',
                        'value': {
                            'detail': 'Data string must be a valid JSON.',
                        }
                    }
                }
            }
        }
    },
}
