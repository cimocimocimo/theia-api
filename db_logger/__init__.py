def get_logger():
    from .signals import DBLogger

    return DBLogger()
