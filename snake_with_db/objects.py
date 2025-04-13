from dataclasses import dataclass

@dataclass
class UserObject:
    id: int
    username: str
    score: int
    level: int