from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class SetVibeRequest(_message.Message):
    __slots__ = ("vibe",)
    VIBE_FIELD_NUMBER: _ClassVar[int]
    vibe: str
    def __init__(self, vibe: _Optional[str] = ...) -> None: ...

class SetVibeResponse(_message.Message):
    __slots__ = ("previous_vibe", "vibe")
    PREVIOUS_VIBE_FIELD_NUMBER: _ClassVar[int]
    VIBE_FIELD_NUMBER: _ClassVar[int]
    previous_vibe: str
    vibe: str
    def __init__(self, previous_vibe: _Optional[str] = ..., vibe: _Optional[str] = ...) -> None: ...

class GetVibeRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetVibeResponse(_message.Message):
    __slots__ = ("vibe",)
    VIBE_FIELD_NUMBER: _ClassVar[int]
    vibe: str
    def __init__(self, vibe: _Optional[str] = ...) -> None: ...
