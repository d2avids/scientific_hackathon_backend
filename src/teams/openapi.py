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
    status.HTTP_201_CREATED: {
        'description': 'Team created successfully'
    }
}

TEAM_UPDATE_RESPONSES = {
    status.HTTP_409_CONFLICT: {
        'description': 'Team with this name already exists'
    },
    **TEAM_NOT_FOUND_RESPONSES
}

TEAM_DELETE_RESPONSES = {
    status.HTTP_204_NO_CONTENT: {
        'description': 'Team deleted successfully'
    },
    **TEAM_NOT_FOUND_RESPONSES
}

TEAM_GET_RESPONSES = {
    **TEAM_NOT_FOUND_RESPONSES,
    status.HTTP_200_OK: {
        'description': 'Team retrieved successfully'
    }
}

TEAM_GET_ALL_RESPONSES = {
    **TEAM_NOT_FOUND_RESPONSES,
    status.HTTP_200_OK: {
        'description': 'Teams retrieved successfully'
    }
}

TEAM_UPDATE_SCHEMA = {
    "requestBody": {
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "update_data": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "example": "string"
                                },
                                "mentorId": {
                                    "type": "integer",
                                    "example": 0
                                },
                                "projectId": {
                                    "type": "integer",
                                    "example": 0
                                },
                                "teamMembers": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {
                                                "type": "integer",
                                                "example": 0
                                            },
                                            "roleName": {
                                                "type": "string",
                                                "example": "string"
                                            },
                                            "participantId": {
                                                "type": "integer",
                                                "example": 0
                                            }
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }
        }
    }
}

TEAM_CREATE_SCHEMA = {
    "requestBody": {
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "team": {
                            "type": "object",
                            "properties": {     
                                "name": {
                                    "type": "string",
                                    "example": "Team Name"
                                },
                                "mentorId": {
                                    "type": "integer",
                                    "example": 1
                                },
                                "projectId": {
                                    "type": "integer",
                                    "example": 1
                                },
                                "teamMembers": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "roleName": {
                                                "type": "string",
                                                "example": "Team Name"
                                            },
                                            "participantId": {
                                                "type": "integer",
                                                "example": 1
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