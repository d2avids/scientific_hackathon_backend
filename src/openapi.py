from fastapi import status

AUTHENTICATION_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: {
        'description': 'Unauthorized scenarios.',
        'content': {
            'application/json': {
                'examples': {
                    'invalid_token': {
                        'summary': 'Invalid token',
                        'value': {
                            'detail': 'Invalid token.',
                        }
                    },
                    'invalid_token_type': {
                        'summary': 'Incorrect token type',
                        'value': {
                            'detail': 'Invalid token. Expected token to be {token_type}.',
                        }
                    },
                    'token_expired': {
                        'summary': 'Token has expired',
                        'value': {
                            'detail': 'Token has expired.'
                        }
                    },
                    'invalid_user_from_token': {
                        'summary': 'User id from token not found in the database',
                        'value': {
                            'detail': 'Could not validate credentials.',
                        }
                    }
                }
            }
        }
    },
    status.HTTP_403_FORBIDDEN: {
        'description': 'Permission denied.',
        'content': {
            'application/json': {
                'example': {
                    'detail': 'You are not allowed to modify or access this resourcez.'
                }
            }
        }
    }
}

FILE_UPLOAD_RELATED_RESPONSES = {
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {
        'description': 'Unsupported photo file format.',
        'content': {
            'application/json': {
                'example': {
                    'detail': 'Unsupported file format. Allowed formats: image/jpeg, image/png, image/bmp.'
                }
            }
        }
    },
    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
        'description': 'File size exceeds the size limit.',
        'content': {
            'application/json': {
                'example': {
                    'detail': 'File size exceeds the limit of 5 MB.'
                }
            }
        }
    },
    status.HTTP_409_CONFLICT: {
        'description': 'Conflict error scenarios.',
        'content': {
            'application/json': {
                'example': {
                    'detail': 'File with filename {file_name} already exists.'
                }
            }
        }
    }
}

NOT_FOUND_RESPONSE = {
    status.HTTP_404_NOT_FOUND: {
        'description': 'Not found.',
    }
}
