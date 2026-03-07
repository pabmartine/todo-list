from dataclasses import dataclass


@dataclass
class Project:
    id: str
    name: str
    color: str

    def to_dict(self):
        return {"id": self.id, "name": self.name, "color": self.color}

