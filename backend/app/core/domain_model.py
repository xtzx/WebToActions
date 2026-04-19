from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, ClassVar, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator


FROZEN_COLLECTION_ERROR = "Collection is frozen."
_DUMP_ADAPTER = TypeAdapter(dict[str, Any])


class FrozenList(Sequence[Any]):
    def __init__(self, items: Iterable[Any] = ()) -> None:
        self._items = tuple(items)

    def __getitem__(self, index: int | slice) -> Any:
        return self._items[index]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return repr(list(self._items))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Sequence) and not isinstance(other, (str, bytes, bytearray)):
            return list(self._items) == list(other)

        return False

    def _raise_frozen(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(FROZEN_COLLECTION_ERROR)

    append = _raise_frozen
    clear = _raise_frozen
    extend = _raise_frozen
    insert = _raise_frozen
    pop = _raise_frozen
    remove = _raise_frozen
    reverse = _raise_frozen
    sort = _raise_frozen
    __delitem__ = _raise_frozen
    __iadd__ = _raise_frozen
    __imul__ = _raise_frozen
    __setitem__ = _raise_frozen


class FrozenDict(Mapping[Any, Any]):
    def __init__(self, items: Mapping[Any, Any] | Iterable[tuple[Any, Any]] = ()) -> None:
        self._items = dict(items)

    def __getitem__(self, key: Any) -> Any:
        return self._items[key]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return repr(self._items)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            return dict(self._items) == dict(other)

        return False

    def _raise_frozen(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(FROZEN_COLLECTION_ERROR)

    clear = _raise_frozen
    pop = _raise_frozen
    popitem = _raise_frozen
    setdefault = _raise_frozen
    update = _raise_frozen
    __delitem__ = _raise_frozen
    __ior__ = _raise_frozen
    __setitem__ = _raise_frozen


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)

        for field_name in self.__class__.model_fields:
            object.__setattr__(
                self,
                field_name,
                _deep_freeze(getattr(self, field_name)),
            )

    def validated_copy(self, **updates: Any) -> Self:
        payload = self._dump_payload()
        payload.update(updates)
        return self.__class__.model_validate(payload)

    def _dump_payload(self) -> dict[str, Any]:
        return {
            field_name: _thaw(getattr(self, field_name))
            for field_name in self.__class__.model_fields
        }

    def model_dump(
        self,
        *,
        mode: Literal["json", "python"] | str = "python",
        include: Any = None,
        exclude: Any = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        exclude_computed_fields: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal["none", "warn", "error"] = True,
        fallback: Callable[[Any], Any] | None = None,
        serialize_as_any: bool = False,
        polymorphic_serialization: bool | None = None,
    ) -> dict[str, Any]:
        payload = self._dump_payload()
        if exclude_none:
            payload = _exclude_none_fields(payload)

        return _DUMP_ADAPTER.dump_python(
            payload,
            mode=mode,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            exclude_computed_fields=exclude_computed_fields,
            round_trip=round_trip,
            warnings=warnings,
            fallback=fallback,
            serialize_as_any=serialize_as_any,
            polymorphic_serialization=polymorphic_serialization,
            context=context,
        )

    def model_dump_json(
        self,
        *,
        indent: int | None = None,
        ensure_ascii: bool = False,
        include: Any = None,
        exclude: Any = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        exclude_computed_fields: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal["none", "warn", "error"] = True,
        fallback: Callable[[Any], Any] | None = None,
        serialize_as_any: bool = False,
        polymorphic_serialization: bool | None = None,
    ) -> str:
        payload = self._dump_payload()
        if exclude_none:
            payload = _exclude_none_fields(payload)

        return _DUMP_ADAPTER.dump_json(
            payload,
            indent=indent,
            ensure_ascii=ensure_ascii,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            exclude_computed_fields=exclude_computed_fields,
            round_trip=round_trip,
            warnings=warnings,
            fallback=fallback,
            serialize_as_any=serialize_as_any,
            polymorphic_serialization=polymorphic_serialization,
            context=context,
        ).decode()


class VersionedArtifactModel(DomainModel):
    version_binding_fields: ClassVar[tuple[str, ...]] = ()
    version_timestamp_fields: ClassVar[tuple[str, ...]] = ()

    id: str = Field(min_length=1)
    version: int = Field(ge=1)
    previous_version: int | None = None

    @model_validator(mode="after")
    def validate_version_chain(self) -> Self:
        if self.version == 1 and self.previous_version is not None:
            raise ValueError("previous_version must be empty for the first artifact version.")

        if self.version > 1 and self.previous_version != self.version - 1:
            raise ValueError(
                "previous_version must point to the immediately preceding artifact version.",
            )

        return self

    def next_version(self, **changes: Any) -> Self:
        protected_fields = ("id", *self.version_binding_fields)
        version_created_at = datetime.now(UTC)

        for field_name in protected_fields:
            if field_name in changes and changes[field_name] != getattr(self, field_name):
                raise ValueError(
                    f"{field_name} must remain stable across artifact versions.",
                )

        timestamp_updates = {
            field_name: version_created_at
            for field_name in self.version_timestamp_fields
            if field_name not in changes
        }

        return self.validated_copy(
            version=self.version + 1,
            previous_version=self.version,
            **timestamp_updates,
            **changes,
        )


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, FrozenList | FrozenDict | DomainModel):
        return value

    if isinstance(value, list):
        return FrozenList(_deep_freeze(item) for item in value)

    if isinstance(value, dict):
        return FrozenDict(
            (key, _deep_freeze(item))
            for key, item in value.items()
        )

    if isinstance(value, tuple):
        return tuple(_deep_freeze(item) for item in value)

    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, FrozenList):
        return [_thaw(item) for item in value]

    if isinstance(value, FrozenDict):
        return {key: _thaw(item) for key, item in value.items()}

    if isinstance(value, DomainModel):
        return {
            field_name: _thaw(getattr(value, field_name))
            for field_name in value.__class__.model_fields
        }

    if isinstance(value, tuple):
        return tuple(_thaw(item) for item in value)

    if isinstance(value, list):
        return [_thaw(item) for item in value]

    if isinstance(value, dict):
        return {key: _thaw(item) for key, item in value.items()}

    return value


def _exclude_none_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _exclude_none_fields(item)
            for key, item in value.items()
            if item is not None
        }

    if isinstance(value, list):
        return [_exclude_none_fields(item) for item in value]

    if isinstance(value, tuple):
        return tuple(_exclude_none_fields(item) for item in value)

    return value
