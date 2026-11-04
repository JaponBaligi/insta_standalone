class InstagramError(Exception):
    '''Base class for all Instagram-related exceptions.'''

class ConfigError(InstagramError):
    '''Raised when there is a configuration error.'''

class GraphAPIError(InstagramError):
    '''Raised when there is an error with the Graph API.'''
    def __init__(self, status_code: int, message: str, code=None, subcode=None, fbtrace_id=None):
        self.status_code = status_code
        self.message = message
        self.code = code
        self.subcode = subcode
        self.fbtrace_id = fbtrace_id
        super().__init__(f"[{status_code}] {message} (code={code}, subcode={subcode})")

class MediaProcessingError(InstagramError):
    '''Raised when there is an error processing media.'''

class MediaTimeoutError(InstagramError):
    '''Raised when there is a timeout error with media processing.'''