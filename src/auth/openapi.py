from fastapi import status

from openapi import AUTHENTICATION_RESPONSES, ResponseDict

LOGIN_RESPONSES: ResponseDict = {
    status.HTTP_401_UNAUTHORIZED: {
        'description': 'Incorrect credentials',
        'content': {
            'application/json': {
                'example':
                    {
                        'detail': 'Incorrect email or password.'
                    }
            }
        }
    },
    status.HTTP_403_FORBIDDEN: {
        'description': 'Not verified account',
        'content': {
            'application/json': {
                'example':
                    {
                        'detail': 'Account not verified yet. Please wait until moderators confirm your registration.'
                    }
            }
        }
    }
}

REFRESH_TOKEN_RESPONSES: ResponseDict = {**AUTHENTICATION_RESPONSES}
REFRESH_TOKEN_RESPONSES.pop(status.HTTP_403_FORBIDDEN)

CHANGE_PASSWORD_RESPONSES: ResponseDict = {
    status.HTTP_403_FORBIDDEN: {
        'description': 'Incorrect old password',
        'content': {
            'application/json': {
                'example':
                    {
                        'detail': 'Incorrect old password.'
                    }
            }
        }

    }
}

RESET_PASSWORD_CALLBACK_RESPONSES: ResponseDict = {
    status.HTTP_403_FORBIDDEN: {
        'description': 'Invalid or expired token',
        'content': {
            'application/json': {
                'example':
                    {
                        'detail': 'Invalid or expired token.'
                    }
            }
        }

    }
}
