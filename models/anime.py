from . import (dataclass, Union, Optional)

@dataclass
class Anime:
    id: Union[str, int]
    title: str 
    image: Optional[str] = None
    synopsis: Optional[str] = None
    type: Optional[str] = None