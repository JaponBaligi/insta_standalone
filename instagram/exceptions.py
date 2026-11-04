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

class CarouselItemError(InstagramError):
    '''Raised when one carousel child fails; the original error is __cause__.'''
    def __init__(self, index: int, media_type: str, cause: Exception):
        self.index = index
        self.media_type = media_type
        super().__init__(f"Carousel item {index} ({media_type}) failed: {cause}")