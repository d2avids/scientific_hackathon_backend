from fastapi import status

TEAM_NOT_FOUND_RESPONSES = {
    status.HTTP_404_NOT_FOUND: {
        'description': 'Team not found'
    }
}

TEAM_CREATE_RESPONSES = {
    status.HTTP_409_CONFLICT: {
        'description': 'Team with this name already exists'
    },
    status.HTTP_400_BAD_REQUEST: {
        'description': 'Invalid team members'
    },
    status.HTTP_201_CREATED: {
        'description': 'Team created successfully'
    }
}

TEAM_UPDATE_RESPONSES = {
    status.HTTP_409_CONFLICT: {
        'description': 'Team with this name already exists'
    },
}

TEAM_DELETE_RESPONSES = {
    status.HTTP_204_NO_CONTENT: {
        'description': 'Team deleted successfully'
    },
}

TEAM_GET_RESPONSES = {
    status.HTTP_200_OK: {
        'description': 'Team retrieved successfully'
    }
}

TEAM_GET_ALL_RESPONSES = {
    status.HTTP_200_OK: {
        'description': 'Teams retrieved successfully'
    }
}

TEAM_CREATE_SCHEMA = {
    'requestBody': {
        'content': {
            'multipart/form-data': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'team': {
                            'type': 'object',
                            'properties': {
                                'name': {
                                    'type': 'string',
                                    'example': 'Team Name'
                                },
                                'mentorId': {
                                    'type': 'integer',
                                    'example': 1
                                },
                                'projectId': {
                                    'type': 'integer',
                                    'example': 1,
                                    'nullable': True
                                },
                                'teamMembers': {
                                    'type': 'array',
                                    'items': {
                                        'type': 'object',
                                        'properties': {
                                            'roleName': {
                                                'type': 'string',
                                                'example': 'Team Name'
                                            },
                                            'participantId': {
                                                'type': 'integer',
                                                'example': 1
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
