from settings import settings


SUCCESSFUL_REGISTRATION_EMAIL_SUBJECT = f'Регистрация на портале «{settings.SITE_NAME}»'
SUCCESSFUL_REGISTRATION_EMAIL_MESSAGE = (
    'Уважаемый пользователь!\n'
    f'Администратор портала «{settings.SITE_NAME}» одобрил Вашу заявку на регистрацию. '
    f'Для доступа к личному кабинету Вы можете перейти к процессу авторизации на портале по следующей ссылке:\n\n'
    f'{settings.auth.FRONTEND_LOGIN_URL}\n\n'
    'Также Вы можете воспользоваться кнопкой «Авторизация» на главной странице портала.\n\n'
    'Ваши данные для входа на портал:\n'
    'Email: {email}\n'
    'Пароль: пароль, указанный при регистрации\n\n'
    'С уважением,\n'
    f'Команда организаторов «{settings.SITE_NAME}»\n'
    f'{settings.SERVER_URL}\n'
    f'{settings.CONTACT_EMAIL}\n'
    f'{settings.CONTACT_PHONE}'
)

REJECTED_REGISTRATION_EMAIL_SUBJECT = f'Регистрация на портале «{settings.SITE_NAME}»'
REJECTED_REGISTRATION_EMAIL_MESSAGE = (
    'Уважаемый пользователь!\n'
    f'Администратор портала «{settings.SITE_NAME}» отклонил Вашу заявку на регистрацию. '
    'Для уточнения причин свяжитесь, пожалуйста, с '
    'организаторами Хакатона по контактам, указанным ниже в подписи к письму. '
    'Также данные контакты можно найти на главной странице портала.\n\n'
    'С уважением,\n'
    f'Команда организаторов «{settings.SITE_NAME}»\n'
    f'{settings.SERVER_URL}\n'
    f'{settings.CONTACT_EMAIL}\n'
    f'{settings.CONTACT_PHONE}'
)

RESET_PASSWORD_EMAIL_SUBJECT = f'Восстановление пароля на портале «{settings.SITE_NAME}»'
RESET_PASSWORD_EMAIL_MESSAGE = (
    'Уважаемый пользователь!\n'
    'К нам поступил запрос на смену пароля вашей учетной записи. Если это вы отправили запрос на смену пароля, '
    'то перейдите по данной ссылке или вставьте ее в адресную строку браузера:\n\n'
    '{reset_link}\n\n'
    'С уважением,\n'
    f'Команда организаторов «{settings.SITE_NAME}»\n'
    f'{settings.SERVER_URL}\n'
    f'{settings.CONTACT_EMAIL}\n'
    f'{settings.CONTACT_PHONE}'
)
