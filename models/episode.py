from . import (dataclass, Union, Optional)
@dataclass
class Episode:
    id: Union[str, int]
    anime: str
    image_preview: Optional[str] = None