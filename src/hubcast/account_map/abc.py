from abc import ABC, abstractmethod
from typing import Union


class AccountMap(ABC):
    """
    An abstract interface defining an account map.
    """

    @abstractmethod
    def __call__(self, src_user: str) -> Union[str, None]:
        """
        Return the corresponding gitlab_user for a given src_user if one exists.
        """
        pass
