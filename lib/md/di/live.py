import inspect
import typing
import builtins

import md.di
import psr.log

from ._di import (
    Configuration,
    Definition,
    Reference,
    dereference,
    reference,
    InvalidDefinitionConfigurationException,
)

_builtin_qualname_set: set = {
    builtins.type.__name__,  # param: type
    'type', 'list', 'set', 'str', 'int', 'dict', 'bool',
    'object', 'float', 'complex', 'bytes', 'bytearray',
    'tuple', 'frozenset',
}

__all__ = ('Container', )


class Container(md.di.Container):
    """ Creates service definition on fly """
    def __init__(self, configuration: Configuration = None) -> None:
        super().__init__(configuration=configuration)
        self._definition_map: typing.Dict[str, Definition] = {}
        self.logger = None

    def set_logger(self, logger: psr.log.LoggerInterface) -> None:
        self.logger = logger

    def get(self, id_: typing.Union[str, type]) -> object:
        try:
            return super().get(id_=id_)
        except Exception as e:
            # FIXME id_ could be an instance, eg. `Exception: Unable to retrieve service `<class 'psr.http.server.RequestHandlerInterface'>``
            raise Exception(f'Unable to retrieve service `{id_!s}`') from e

    def _get_definition(self, id_: str) -> Definition:
        """ Returns class definition if exists or creates new else """
        if id_ in self._configuration.definition_alias_map:
            id_ = self._configuration.definition_alias_map[id_]

        if id_ not in self._definition_map:
            if id_ in self._configuration.definition_map:
                class_ = self._configuration.definition_map[id_].class_
            else:  # fixme cleanup this scope
                class_ = dereference(class_qualname=id_)
                implicit_id = reference(id_=class_, explicit=False)

                if implicit_id in self._configuration.definition_map:
                    definition_class = self._configuration.definition_map[implicit_id].class_
                    assert definition_class is class_
                    id_ = implicit_id

            self._definition_map[id_] = self._create_definition(id_=id_, class_=class_)

        return self._definition_map[id_]

    def _create_definition(self, class_: type = None, id_: str = None) -> Definition:
        assert class_ or id_, 'At least one argument is required'

        id_ = id_ or reference(id_=class_, explicit=False)
        assert id_ not in self._configuration.definition_alias_map, 'Aliased service id must be resolved'

        if id_ in self._configuration.definition_map:
            definition = self._configuration.definition_map[id_]

            if definition.class_:
                assert isinstance(definition.class_, type)
                factory = definition.class_.__init__

            if definition.factory:
                f = None
                v = None

                if isinstance(definition.factory, (list, tuple)):  # todo replace with `tuple` only
                    assert len(definition.factory) == 2
                    f, v = definition.factory

                if isinstance(definition.factory, Reference):
                    f = self._get_instance(id_=definition.factory.id)
                    factory = f

                if isinstance(v, str):
                    factory = getattr(f, v)
                # else ..
                if callable(definition.factory):
                    factory = definition.factory

            factory_signature = inspect.signature(obj=factory)

            has_var_keyword = False  # **kwargs
            for factory_parameter_signature in factory_signature.parameters.values():
                if factory_parameter_signature.kind == factory_parameter_signature.VAR_KEYWORD:
                    has_var_keyword = True
                    break

            for argument in definition.arguments:  # validate definition
                if argument not in factory_signature.parameters:
                    if has_var_keyword:
                        # when definition parameter is provided,  no such parameter found,
                        # but function has `**kwargs`, skip validation
                        break

                    raise InvalidDefinitionConfigurationException(
                        f'Invalid definition: parameter `{argument!s}` not found in `{id_!s}`'
                    )

                if isinstance(factory_signature.parameters[argument].annotation, str):
                    # e.g. `def __init__(self, test: 'module.Class') -> None`
                    continue  # todo: implement check

                if factory_signature.parameters[argument].annotation.__module__ == 'typing':
                    continue  # todo: implement check

                if isinstance(definition.arguments[argument], Reference):
                    # fixme get definition by id and compare with typehint
                    continue

                if factory_signature.parameters[argument].annotation is not inspect.Signature.empty:
                    if not isinstance(definition.arguments[argument], factory_signature.parameters[argument].annotation):
                        # fixme !! typehint may be not provided
                        raise InvalidDefinitionConfigurationException(
                            f'Invalid definition: type of `{argument!s}` argument must be '
                            f'`{reference(id_=factory_signature.parameters[argument].annotation)!s}`, '
                            f'`{reference(definition.arguments[argument])!s}` given.'
                        )
        else:
            if id_.lower().endswith('interface'):
                raise Exception(f'Cannot autowire interface `{id_!s}`')  # fixme wrong exception when interface is asked as a service from container

            assert class_
            factory_signature = inspect.signature(class_.__init__)
            definition = Definition(class_=class_, public=True)

            if self.logger:
                self.logger.debug('definition created', {'id': id_})

        # fixme lambda could be used in factory instead, and has no parameters
        # if 'self' not in factory.parameters:
        #     raise NotImplementedError

        for argument in factory_signature.parameters:  # autowire
            if argument == 'self':  # fixme weak
                continue

            if argument in definition.arguments:
                continue  # skip wired argument (with definition)

            argument_signature = factory_signature.parameters[argument]

            if (
                argument_signature.kind is inspect.Parameter.VAR_KEYWORD
                or argument_signature.kind is inspect.Parameter.VAR_POSITIONAL
            ):
                continue  # fixme

            if argument_signature.default is not inspect.Parameter.empty:
                definition.arguments[argument] = argument_signature.default
                continue

            if isinstance(argument_signature.annotation, str):
                """ string annotation case, eg: def __init__(self, argument: 'string_path') """
                if argument_signature.annotation in _builtin_qualname_set:  # TODO CHECK THIS NAME IN MODULE AS ATTR, BEFORE BULTINS
                    raise Exception('buidfs')  # fixme

                class_path_list = argument_signature.annotation.split('.')
                resolved_class = inspect.getmodule(class_)

                try:
                    for class_path in class_path_list[:-1]:
                        resolved_class = getattr(resolved_class, class_path)
                except AttributeError:
                    raise InvalidDefinitionConfigurationException(
                        f'Unable to create definition `{id_!s}`: unable to autowire `{argument!s}` argument, unknown type. '
                        f'Provided class can not be resolved.'
                    )

                definition.arguments[argument] = Reference(id_=resolved_class.__name__ + '.' + class_path_list[-1])
                continue

            if argument_signature.annotation.__module__ == 'typing':
                raise InvalidDefinitionConfigurationException(
                    f'Unable to create definition `{id_!s}`: unable to autowire `{argument!s}: {argument_signature.annotation}` argument'
                )
                # continue  # todo: implement check

            if argument_signature.annotation is None and argument_signature.default is inspect.Parameter.empty:
                raise InvalidDefinitionConfigurationException(
                    f'Unable to create definition `{id_!s}`: unable to autowire `{argument!s}` argument'
                )

            argument_class_qualname = reference(argument_signature.annotation)
            if argument_class_qualname in _builtin_qualname_set:
                raise InvalidDefinitionConfigurationException(
                    f'Unable to create definition `{id_!s}`: unable to autowire `{argument!s}` argument'
                )

            definition.arguments[argument] = Reference(id_=argument_class_qualname)
        return definition
