

class PBEExportException(Exception):

    """ This exception is thrown whenever an error occurs during the export 
    process. This way we can propagate them easily through the hierarchy, without
    having to check the return status of each function """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message
