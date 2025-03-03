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
