from fastapi import status

from openapi import FILE_UPLOAD_RELATED_RESPONSES, ResponseDict

PROJECT_CREATE_UPDATE_SCHEMA = {
    'requestBody': {
        'content': {
            'multipart/form-data': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'data': {
                            'type': 'object',
                            'properties': {
                                'name': {
                                    'type': 'string',
                                    'example': 'Project 1',
                                    'nullable': False,
                                },
                                'description': {
                                    'type': 'string',
                                    'example': 'This is a description of a project',
                                    'nullable': False,
                                },
                            }
                        },
                        'document': {
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

PROJECT_CREATE_RESPONSES: ResponseDict = {
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

STEP_START_ATTEMPT_RESPONSES: ResponseDict = {
    status.HTTP_409_CONFLICT: {
        'description': 'Invalid JSON in project_data field or data string must be a valid JSON.',
        'content': {
            'application/json': {
                'examples': {
                    'previous_step_not_finished': {
                        'summary': 'Attempt to start the step when the previous step is not finished',
                        'value': {
                            'detail': 'Cannot start the new step until the previous step is finished',
                        }
                    },
                    'step_already_started': {
                        'summary': 'Attempt to start the step that has been already started',
                        'value': {
                            'detail': 'Step is already started'
                        }
                    }
                }
            }
        }
    },
}

STEP_SUBMIT_ATTEMPT_RESPONSES: ResponseDict = {
    status.HTTP_409_CONFLICT: {
        'description': 'Cannot submit the step due to its current state',
        'content': {
            'application/json': {
                'examples': {
                    'step_not_started': {
                        'summary': 'Attempt to submit a step that has not been started',
                        'value': {
                            'detail': 'Cannot submit step. First, start the step',
                        }
                    }
                }
            }
        }
    },
    **FILE_UPLOAD_RELATED_RESPONSES
}

MODIFY_STEP_ATTEMPT_RESPONSES: ResponseDict = {
    status.HTTP_409_CONFLICT: {
        'description': 'Cannot accept or reject the step due to its current state',
        'content': {
            'application/json': {
                'examples': {
                    'step_not_submitted': {
                        'summary': 'Attempt to accept or reject a step that has not been submitted',
                        'value': {
                            'detail': 'Step has not been submitted',
                        }
                    },
                    'time_exceeded_no_timer': {
                        'summary': 'Time exceeded but no new timer provided',
                        'value': {
                            'detail': 'Step\'s time exceeded. New timer value is required',
                        }
                    }
                }
            }
        }
    }
}

COMMENT_CREATE_RESPONSES: ResponseDict = {
    status.HTTP_400_BAD_REQUEST: {
        'description': 'Invalid request',
        'content': {
            'application/json': {
                'examples': {
                    'too_many_files': {
                        'summary': 'Too many files uploaded',
                        'value': {
                            'detail': 'Too many files to send. Maximum is 5',
                        }
                    },
                }
            }
        }
    },
    status.HTTP_409_CONFLICT: {
        'description': 'Step not started',
        'application/json': {
            'examples': {
                'step_not_started': {
                    'summary': 'Step not started',
                    'value': {
                        'detail': 'Step has not been started',
                    }
                },
            }
        }

    }
}
