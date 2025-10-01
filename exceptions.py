"""
Custom exceptions for Recall AI
"""


class RecallAIException(Exception):
    """Base exception for Recall AI"""
    pass


class ConfigurationError(RecallAIException):
    """Configuration related errors"""
    pass


class DatabaseError(RecallAIException):
    """Database related errors"""
    pass


class ProcessingError(RecallAIException):
    """File/content processing errors"""
    pass


class AuthenticationError(RecallAIException):
    """Authentication/authorization errors"""
    pass


class RateLimitError(RecallAIException):
    """Rate limiting errors"""
    pass


class FileSizeError(ProcessingError):
    """File size limit exceeded"""
    pass


class UnsupportedFileTypeError(ProcessingError):
    """Unsupported file type"""
    pass


class AIServiceError(RecallAIException):
    """AI service related errors"""
    pass
