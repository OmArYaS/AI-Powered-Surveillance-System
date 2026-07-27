from abc import ABC, abstractmethod

import numpy as np


class StreamRepository(ABC):
    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def get_frame(self) -> np.ndarray | None: ...

    @property
    @abstractmethod
    def is_connected(self) -> bool: ...
