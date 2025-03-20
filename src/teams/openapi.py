from typing import Any, Dict

from fastapi import status

ResponseDict = Dict[int | str, Dict[str, Any]]

TEAM_NOT_FOUND_RESPONSES: ResponseDict = {
    status.HTTP_404_NOT_FOUND: {
        'description': 'Team not found'
    }
}

TEAM_CREATE_RESPONSES: ResponseDict = {
    status.HTTP_409_CONFLICT: {
        'description': 'Team with this name already exists',
        'content': {
            'application/json': {
                'example': {
                    'detail': 'Team with this name already exists'
                }
            }
        }
    },
    status.HTTP_400_BAD_REQUEST: {
        'description': 'Invalid team or team members data',
        'content': {
            'application/json': {
                'examples': {
                    'invalid_team_data': {
                        'summary': 'Invalid team data',
                        'value': {
                            'detail': 'Invalid team data'
                        }
                    },
                    'invalid_team_members_data': {
                        'summary': 'Invalid team members data',
                        'value': {
                            'detail': 'Invalid team members data'
                        }
                    }
                }
            }
        }
    },
    status.HTTP_201_CREATED: {
        'description': 'Team created successfully'
    }
}

TEAM_UPDATE_RESPONSES: ResponseDict = {
    status.HTTP_409_CONFLICT: {
        'description': 'Team with this name already exists'
    },
}

TEAM_DELETE_RESPONSES: ResponseDict = {
    status.HTTP_204_NO_CONTENT: {
        'description': 'Team deleted successfully'
    },
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
