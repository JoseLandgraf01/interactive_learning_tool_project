from __future__ import annotations


class LearningToolError(Exception):
    """Base exception for all errors in the learning tool project.  # NF3"""


class PersistenceError(LearningToolError):
    """Raised when reading or writing questions data fails.  # NF3"""


class QuestionValidationError(LearningToolError):
    """Raised when a Question instance has inconsistent or invalid data.  # NF3"""


class LLMError(LearningToolError):
    """Raised when an error occurs while calling or parsing the LLM.  # NF3"""
