from . import (dataclass, Union, Optional)

@dataclass
class Anime:
    id: Union[str, int]
    title: str 
    image: Optional[str] = None
    synopsis: Optional[str] = None
    type: Optional[str] = None

    @property
    def data(self):
        return {
            "id": self.id,
            "title": self.title,
            "image": self.image,
            "synopsis": self.synopsis,
            "type": self.type
        }