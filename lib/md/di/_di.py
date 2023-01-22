# fixme check argument type (CLASS) corresponds to typehint (CLASS) !
#  todo consider to implement independent container call, to make possible (eg. subscribe FUNCTION on EVENT_DISPATCHER)
#  todo add typing.Set, etc, fixme: here is recursion so make it as property

import typing

import psr.container
import md.python

# Metadata
__author__ = 'https://md.land/md'
__version__ = '0.1.0'
__all__ = (
    # Metadata
    '__author__',
    '__version__',
    # Type (consider to exclude)
    'FactoryType',
    'DefinitionTagType',
    'DefinitionCallType',
    # Exceptions
    'ClassNotFoundException',
    'ServiceCircularReferenceException',
    'InvalidDefinitionConfigurationException',
    # Entities
    'Reference',
    'Definition',
    'Callable',
    'Configuration',
    # Components
    'Container',
    # Internals
    'dereference',
    'reference',
)


# Type
FactoryType = typing.Union[
    typing.Tuple[
        typing.Union[
            'Reference',
            type  # module or class (type)
        ],
        str  # function or method name
    ],
    typing.Callable[  # cls
        ...,  # definition arguments
        object  # service instance
    ]
]
DefinitionTagType = typing.Dict[str, typing.Any]
DefinitionCallType = typing.Tuple[
    str,  # method name
    typing.Tuple[typing.Any],  # sequential method argument list
    typing.Dict[str, typing.Any]  # named method arguments dictionary
]


# Exception
class ClassNotFoundException(RuntimeError, psr.container.ContainerExceptionInterface):
    pass


class ServiceCircularReferenceException(RuntimeError, psr.container.ContainerExceptionInterface):
    pass


class InvalidDefinitionConfigurationException(RuntimeError, psr.container.ContainerExceptionInterface):
    pass


# Entity
class Reference:
    """ References to a service definition """
    def __init__(self, id_: str) -> None:
        self.id = id_

    def __repr__(self) -> str:
        return f'Reference(id_={self.id!r})'


class Definition:
    """ Service definition — the instruction how to build service """
    def __init__(
        self,
        class_: typing.Optional[type] = None,
        factory: typing.Optional[FactoryType] = None,
        arguments: typing.Dict[str, typing.Any] = None,
        calls: typing.List[DefinitionCallType] = None,
        public: bool = False,
        shared: bool = True,
        tags: typing.List[DefinitionTagType] = None,
    ) -> None:
        assert (class_ is None) ^ (factory is None), 'Only one of `cls` and `class` options allowed'

        self.class_ = class_
        self.factory = factory
        self.arguments = arguments or {}
        self.calls = calls or []
        self.public = public
        self.shared = shared
        self.tags = tags or []

    def has_tag(self, tag: str) -> bool:
        # Warning: case-sensitive
        for tag_ in self.tags:
            if tag_['name'] == tag:
                return True
        return False

    def find_tags(self, tag: str) -> typing.Iterable[DefinitionTagType]:
        # Warning: case-sensitive
        for tag_ in self.tags:
            if tag_['name'] == tag:
                yield tag_

    def __repr__(self) -> str:
        class_ = f'dereference("{reference(self.class_)!r}")' if self.class_ else None

        return f'Definition(' \
            f'class_={class_!s}, factory={self.factory!r}, '\
            f'arguments={self.arguments!r}, calls={self.calls!r}, ' \
            f'public={self.public!r}, shared={self.shared!r}, tags={self.tags!r})'


class Callable:
    def __init__(self, holder: typing.Union[Reference], method: str) -> None:
        self.holder = holder
        self.method = method

    def __repr__(self) -> str:
        return f'Callable(holder={self.holder!r}, method={self.method!r})'


class Configuration:
    """ Container configuration """
    def __init__(
        self,
        parameter_map: typing.Dict[str, typing.Any] = None,
        definition_map: typing.Dict[str, Definition] = None,
        definition_alias_map: typing.Dict[str, str] = None,
    ) -> None:
        self.parameter_map = parameter_map or {}
        self.definition_map: typing.Dict[str, Definition] = definition_map or {}
        self.definition_alias_map: typing.Dict[str, str] = definition_alias_map or {}

    def __repr__(self) -> str:
        return (
            f'Configuration(parameter_map={self.parameter_map!r},'
            f'definition_map= {self.definition_map!r},'
            f'definition_alias_map= {self.definition_alias_map!r},)'
        )


# Components
class Container(psr.container.ContainerInterface):
    """ Not thread-safe """
    def __init__(self,  configuration: Configuration = None) -> None:
        self._configuration = configuration if configuration else Configuration()

        self._configuration.definition_alias_map.update({
            'container': 'md.di.Container',
            'psr.container.ContainerInterface': 'md.di.Container',
        })

        self._configuration.definition_map['md.di.Container'] = Definition(factory=lambda: self)  # hack  # FIXME

        # runtime
        self._instance_map: typing.Dict[str, object] = {
            'md.di.Container': self  # synthetic service
        }
        self._loading_service_list: typing.List[str] = []  # stack of loading services

    def _get_definition(self, id_: str) -> Definition:
        """ Returns class definition if exists (or alias destination)"""
        if id_ in self._configuration.definition_alias_map:
            id_ = self._configuration.definition_alias_map[id_]

        if id_ not in self._configuration.definition_map:
            raise ClassNotFoundException(f'Definition `{id_!s}` not found')

        return self._configuration.definition_map[id_]

    def _resolve_argument(self, argument: typing.Any) -> typing.Any:
        if isinstance(argument, Reference):
            return self._get_instance(id_=argument.id)

        if isinstance(argument, Definition):  # todo consider to remove this scope in favor for pre-resolution & reference to it
            return self._get_instance(
                id_=str(hash(argument)),  # fixme what if argument is not hashable ?
                definition=argument,
            )

        if isinstance(argument, Callable):
            return self._resolve_callable(holder_reference=argument.holder, method_name=argument.method)

        if isinstance(argument, list):  # todo consider to use iterable instead
            for index, value in enumerate(argument):
                argument[index] = self._resolve_argument(argument=value)  # todo check is overriding is ok ?
            return argument

        if isinstance(argument, dict):
            for key, value in argument.items():
                argument[key] = self._resolve_argument(argument=value)  # todo check is overriding is ok ?
            return argument
        return argument

    def _get_instance(self, id_: str, definition: Definition = None) -> object:
        try:
            definition = definition or self._get_definition(id_=id_)  # aliased or native id is here, get native definition
        except Exception as e:
            raise Exception(f'Unable to retrieve service instance `{id_!s}`') from e  # fixme

        if not definition.shared:  # if service id is aliased, then check is resolved definition shared
            return self._create_instance(id_=id_, definition=definition)

        if id_ in self._configuration.definition_alias_map:
            # if service is aliased, then use destination definition instance
            id_ = self._configuration.definition_alias_map[id_]

        if id_ not in self._instance_map:
            self._create_instance(id_=id_, definition=definition)
            assert id_ in self._instance_map

        return self._instance_map[id_]

    def _resolve_factory(self, factory: FactoryType) -> typing.Callable[..., object]:
        if isinstance(factory, tuple):
            holder_reference, method_name = factory
            return self._resolve_callable(holder_reference, method_name)

        if callable(factory):  # todo consider to check does it requires arguments ?
            return factory

        if isinstance(factory, Reference):
            instance = self._get_instance(id_=factory.id)
            assert callable(instance)
            return instance

        raise NotImplementedError

    def _resolve_callable(self, holder_reference: typing.Union[type, Reference], method_name: str) -> typing.Callable:
        holder = holder_reference

        if isinstance(holder_reference, Reference):
            holder = self._get_instance(id_=holder_reference.id)

        resolved_callable = holder
        if method_name:
            try:
                resolved_callable = getattr(holder, method_name)
            except TypeError as e:
                raise InvalidDefinitionConfigurationException(
                    'Holder does not supports attribute access'  # fixme message
                ) from e
            except AttributeError as e:
                # this check could not be moved into validation on build phase, because it could be magic method
                raise InvalidDefinitionConfigurationException(
                    'Method not exists'  # fixme or remove at all in favor of validation on build phase
                ) from e

        assert callable(resolved_callable)
        return resolved_callable

    def _create_instance(self, id_: str, definition: Definition) -> object:
        """ Creates and returns new instance """

        if id_ in self._loading_service_list:
            raise ServiceCircularReferenceException(
                f'The service `{id_!s}` has a circular reference to itself: ' +
                ' -> '.join(self._loading_service_list + [id_])
            )

        self._loading_service_list.append(id_)

        # todo consider to add support for list arguments

        resolved_argument_map = {}
        for argument_key, argument_value in definition.arguments.items():
            resolved_argument_map[argument_key] = self._resolve_argument(argument=argument_value)

        self._loading_service_list.pop()

        factory = definition.class_

        if definition.factory:
            factory = self._resolve_factory(factory=definition.factory)

        try:
            instance = factory(**resolved_argument_map)
        except TypeError as e:  # should never happen
            raise InvalidDefinitionConfigurationException(
                f'Unable to initialize service `{id_!s}`. Definition has invalid configuration.'
            ) from e
        except Exception as e:
            raise InvalidDefinitionConfigurationException(
                f'Unable to initialize service `{id_!s}`'
            ) from e

        self._instance_map[id_] = instance

        for method_name, argument_list, argument_map in definition.calls:
            try:
                instance_method = getattr(instance, method_name)
            except AttributeError as e:
                # this check could not be fully moved into validation on build phase, because method could be magic
                raise InvalidDefinitionConfigurationException(
                    f'Unable to initialize service. Definition `{id_!s}` has no method `{method_name!s}`'
                ) from e

            # Resolve arguments
            resolved_argument_list = []
            for argument_value in argument_list:
                resolved_argument_list.append(self._resolve_argument(argument=argument_value))

            resolved_argument_map = {}
            for argument_key, argument_value in argument_map.items():
                resolved_argument_map[argument_key] = self._resolve_argument(argument=argument_value)

            # Perform call
            instance_method(*resolved_argument_list, **resolved_argument_map)

        return instance

    def get(self, id_: typing.Union[str, type]) -> object:
        id_ = reference(id_=id_)
        definition = self._get_definition(id_=id_)

        if not definition.public:
            raise InvalidDefinitionConfigurationException(f'Definition `{id_!s}` is private')

        return self._get_instance(id_=id_, definition=definition)

    def has(self, id_: typing.Union[str, type]) -> bool:
        try:
            definition = self._get_definition(id_=reference(id_=id_))
        except ClassNotFoundException:
            return False

        if not definition.public:
            return False

        if not definition.shared:
            return False

        return True

    def set(self, id_: str, instance: object) -> None:
        # todo consider to check is instance exists
        # todo consider to check is definition id exists
        self._instance_map[id_] = instance


# Internals
def dereference(class_qualname: str) -> type:
    """ Dereferences string class pointer to a class object """
    try:
        definition = md.python.dereference(reference_=class_qualname)
    except md.python.DereferenceException as e:
        raise ClassNotFoundException(f'Unable to resolve `{class_qualname!s}`') from e

    if not isinstance(definition, type):
        raise ClassNotFoundException(f'`{class_qualname!s}` is not a class')

    return definition


def reference(id_: typing.Union[str, type], explicit: bool = True) -> str:
    """ References class object to a string pointer """
    return md.python.reference(definition=id_, explicit=explicit)
