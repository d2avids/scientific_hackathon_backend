import copy

from fastapi import status
from openapi import FILE_UPLOAD_RELATED_RESPONSES

USER_GET_RESPONSES = {
    status.HTTP_404_NOT_FOUND: {
        'description': 'User not found',
        'content': {
            'application/json': {
                'example': {
                    'detail': 'User not found.'
                }
            }
        }
    }
}

USER_CREATE_RESPONSES = {
    status.HTTP_409_CONFLICT: {
        'description': 'User already exists or region_id does not exist',
        'content': {
            'application/json': {
                'example': {
                    'detail': 'User with this email already exists OR region_id does not exist.'
                }
            }
        }
    }
}

USER_UPDATE_RESPONSES = {
    **FILE_UPLOAD_RELATED_RESPONSES,
    status.HTTP_400_BAD_REQUEST: {
        'description': 'Invalid JSON in user_data field or data string must be a valid JSON.',
        'content': {
            'application/json': {
                'examples': {
                    'region_does_not_exist': {
                        'summary': 'Region with provided region_id does not exist',
                        'value': {
                            'detail': 'Region does not exist.',
                        }
                    },
                    'invalid_user_data': {
                        'summary': 'Invalid JSON in user_data field',
                        'value': {
                            'detail': 'Invalid JSON in user_data field.',
                        }
                    },
                    'not_json_user_data': {
                        'summary': 'user_data string is not convertable to json',
                        'value': {
                            'detail': 'Data string must be a valid JSON.',
                        }
                    }
                }
            }
        }
    },
    status.HTTP_422_UNPROCESSABLE_ENTITY: {
        'description': 'Data validation error. Model validation failed.',
        'content': {
            'application/json': {
                'example': {
                    'detail': [
                        {
                            'type': 'value_error',
                            'loc': [],
                            'msg': 'Value error, firstName cannot be null if explicitly passed',
                            'input': {
                                'firstName': ''
                            }
                        }
                    ]
                }
            }
        }
    },
}

USER_UPDATE_SCHEMA = {
    'requestBody': {
        'content': {
            'multipart/form-data': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'data': {
                            'type': 'object',
                            'properties': {
                                'firstName': {
                                    'type': 'string',
                                    'example': 'John',
                                    'nullable': False,
                                },
                                'lastName': {
                                    'type': 'string',
                                    'example': 'Doe',
                                    'nullable': False,
                                },
                                'patronymic': {
                                    'type': 'string',
                                    'example': 'Ivanovich',
                                    'nullable': True,
                                },
                                'phoneNumber': {
                                    'type': 'string',
                                    'example': '79999009090',
                                    'nullable': False,
                                },
                                'eduOrganization': {
                                    'type': 'string',
                                    'example': 'Some Name',
                                    'nullable': False,
                                },
                                'about': {
                                    'type': 'string',
                                    'example': 'Some Name',
                                    'nullable': True,
                                },
                                'participant': {
                                    'type': 'object',
                                    'properties': {
                                        'regionId': {
                                            'type': 'integer',
                                            'example': 1,
                                            'nullable': False
                                        },
                                        'schoolGrade': {
                                            'type': 'string',
                                            'example': '10',
                                            'nullable': False
                                        },
                                        'birthDate': {
                                            'type': 'string',
                                            'format': 'date',
                                            'example': '2005-03-03',
                                            'nullable': False
                                        },
                                        'city': {
                                            'type': 'string',
                                            'example': 'City',
                                            'nullable': False
                                        },
                                        'interests': {
                                            'type': 'string',
                                            'example': 'coding',
                                            'nullable': True
                                        },
                                        'olympics': {
                                            'type': 'string',
                                            'example': 'none',
                                            'nullable': True
                                        },
                                        'achievements': {
                                            'type': 'string',
                                            'example': 'awarded',
                                            'nullable': True
                                        }
                                    }
                                },
                                'mentor': {
                                    'type': 'object',
                                    'properties': {
                                        'specialization': {
                                            'type': 'string',
                                            'example': 'Math',
                                            'nullable': False
                                        },
                                        'jobTitle': {
                                            'type': 'string',
                                            'example': 'Teacher',
                                            'nullable': False
                                        },
                                        'researchTopics': {
                                            'type': 'string',
                                            'example': 'Algebra',
                                            'nullable': True
                                        },
                                        'articles': {
                                            'type': 'string',
                                            'example': 'published',
                                            'nullable': True
                                        },
                                        'scientificInterests': {
                                            'type': 'string',
                                            'example': 'research',
                                            'nullable': True
                                        },
                                        'taughtSubjects': {
                                            'type': 'string',
                                            'example': 'math',
                                            'nullable': True
                                        }
                                    }
                                }
                            }
                        },
                        'photo': {
                            'type': 'string',
                            'format': 'binary',
                            'nullable': True
                        }
                    }
                }
            }
        }
    }
}

USER_DOCUMENTS_CREATE_RESPONSES = copy.deepcopy(FILE_UPLOAD_RELATED_RESPONSES)
USER_DOCUMENTS_CREATE_RESPONSES[status.HTTP_409_CONFLICT] = {
    'description': 'Conflict error scenarios.',
    'content': {
        'application/json': {
            'schema': {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string'},
                }
            },
            'examples': {
                'file_exists': {
                    'summary': 'File already exists',
                    'value': {
                        'detail': 'File with filename {file_name} already exists.',
                    }
                },
                'maximum_documents': {
                    'summary': 'Other conflict scenario',
                    'value': {
                        'detail': 'Maximum amount of documents ({docs_number}) are already created for this user.',
                    }
                }
            }
        }
    }
}

USER_VERIFY_RESPONSES = {
    status.HTTP_404_NOT_FOUND: {
        "description": "User not found.",
        "content": {
            "application/json": {
                "example": {"detail": "User not found."}
            }
        }
    },
    status.HTTP_409_CONFLICT: {
        "description": "User is already verified.",
        "content": {
            "application/json": {
                "example": {"detail": "User is already verified."}
            }
        }
    },
}
