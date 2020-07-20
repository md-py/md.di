import importlib as _import
import typing as _typing

import psr.container


__version__ = '0.1.0'

_builtin_qualname_set: set = {  # todo consider to refactor to tuple: it's immutable ds
    'type', 'list', 'set', 'str', 'int', 'dict', 'bool',
    'object', 'float', 'complex', 'bytes', 'bytearray',
    'tuple', 'frozenset',
}


# todo add typing.Set, etc, fixme: here is recursion so make it as property

# Type

_DefinitionTagType = _typing.Dict


# Exception

class ClassNotFoundException(psr.container.ContainerExceptionInterface):
    pass


class ServiceCircularReferenceException(psr.container.ContainerExceptionInterface):
    pass


class InvalidDefinitionConfigurationException(psr.container.ContainerExceptionInterface):
    pass


# Entity

class Definition:
    def __init__(
            self,
            class_: type,
            arguments: dict = None,
            public: bool = False,
            shared: bool = True,
            tags: _typing.List[_DefinitionTagType] = None,
    ):
        self.class_: type = class_
        self.arguments: dict = arguments if arguments else {}
        self.public: bool = public
        self.shared: bool = shared
        self.tags: _typing.List[_DefinitionTagType] = tags if tags else []

    def has_tag(self, tag: str) -> bool:
        for tag_ in self.tags:
            if tag_['name'] == tag:
                return True
        return False

    def find_tags(self, tag: str) -> _typing.Iterable[_DefinitionTagType]:
        for tag_ in self.tags:
            if tag_['name'] == tag:
                yield tag_

    def __repr__(self) -> str:
        return f'Definition(' \
            f'class_={self.class_!r}, arguments={self.arguments!r}, ' \
            f'public={self.public!r}, shared={self.shared!r}, tags={self.tags!r})'


class Reference:
    def __init__(self, id_: str):
        self.id = id_

    def __repr__(self) -> str:
        return f'Reference(id_={self.id!r})'


# Container


class Configuration:
    def __init__(
            self,
            parameter_map: _typing.Dict[str, _typing.Any] = None,
            definition_map: _typing.Dict[str, Definition] = None,
    ):
        self.parameter_map = parameter_map if parameter_map else {}
        self.definition_map: _typing.Dict[str, Definition] = definition_map


class Container(psr.container.ContainerInterface):
    """ Not thread-safe """
    def __init__(self, configuration: Configuration = None):
        self._configuration = configuration if configuration else Configuration()

        # runtime
        self._instance_map: _typing.Dict[str, object] = {}
        self._loading_service_list: _typing.List[str] = []  # stack of loading services

    def _get_definition(self, id_: str) -> Definition:
        """ Returns class definition if exists or creates new else """

        if id_ not in self._configuration.definition_map:
            raise ClassNotFoundException(f'Definition `{id_!s}` not found')

        return self._configuration.definition_map[id_]

    def _resolve_argument(self, argument: _typing.Any) -> _typing.Any:
        if isinstance(argument, Reference):
            return self._get_instance(
                id_=argument.id,
                definition=self._get_definition(id_=argument.id),
            )

        if isinstance(argument, Definition):  # todo consider to remove this scope in favor for pre-resolution & reference to it
            return self._get_instance(
                id_=str(hash(argument)),
                definition=argument,
            )

        if isinstance(argument, list):  # todo consider to use iterable instead
            for index, value in enumerate(argument):
                argument[index] = self._resolve_argument(value)

        return argument

    def _get_instance(self, id_: str, definition: Definition) -> object:
        if not definition.shared:
            return self._create_instance(id_=id_, definition=definition)

        if id_ not in self._instance_map:
            self._instance_map[id_] = self._create_instance(id_=id_, definition=definition)

        return self._instance_map[id_]

    def _create_instance(self, id_: str, definition: Definition) -> object:
        """ Creates and returns new instance """

        if id_ in self._loading_service_list:
            raise ServiceCircularReferenceException(
                f'The service `{id_!s}` has a circular reference to itself: ' +
                ' -> '.join(self._loading_service_list)
            )

        self._loading_service_list.append(id_)

        resolved_argument_map = {}
        for argument_key, argument_value in definition.arguments.items():
            resolved_argument_map[argument_key] = self._resolve_argument(argument=argument_value)

        self._loading_service_list.pop()

        try:
            return definition.class_(**resolved_argument_map)
        except TypeError as e:  # should never happen
            raise InvalidDefinitionConfigurationException(
                f'Unable to initialize service `{id_!s}`. Definition has invalid configuration.'
            ) from e

    def get(self, id_: _typing.Union[str, type]) -> object:
        definition = self._get_definition(id_=reference(id_=id_))

        if not definition.public:
            raise InvalidDefinitionConfigurationException(f'Definition `{id_!s}` is private')

        return self._get_instance(id_=id_, definition=definition)

    def has(self, id_: _typing.Union[str, type]) -> bool:
        definition = self._get_definition(id_=reference(id_=id_))

        if not definition.public:
            return False

        if not definition.shared:
            return False

        return True


def dereference(class_qualname: str) -> type:
    """ Dereferences string class pointer to a class object """
    module_name, class_name = class_qualname.rsplit('.', 1)

    # fixme: wrap module importing in try/except block
    module: type = _import.import_module(name=module_name)

    try:
        return getattr(module, class_name)
    except AttributeError as e:
        raise ClassNotFoundException(f'Unable to resolve `{class_qualname!s}` class') from e


def reference(id_: _typing.Union[str, type]) -> str:
    """ References class object to a string pointer """
    if isinstance(id_, type):
        module = id_.__module__
        if module is None or module == str.__class__.__module__:
            return id_.__class__.__name__
        return module + '.' + id_.__name__
    return id_
