from abc import ABC, abstractmethod
from typing import Union


class AccountMap(ABC):
    """
    An abstract interface defining an account map.
    """

    @abstractmethod
    def __call__(self, github_user: str) -> Union[str, None]:
        """
        Return the coorisponding gitlab_user for a given github_user if
        one exists.
        """
        pass
