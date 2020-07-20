import inspect as _inspect
import typing as _typing

from ._di import (
    Container as StaticContainer,
    Configuration,
    Definition,
    Reference,
    dereference,
    reference,
    InvalidDefinitionConfigurationException,
    _builtin_qualname_set
)


class Container(StaticContainer):  # todo move to `md.di.container.live.Container`  # / Mutable / Immutable
    """ Creates service definition on fly """
    def __init__(self, configuration: Configuration = None):
        super().__init__(configuration=configuration)
        self._definition_map: _typing.Dict[str, Definition] = {}

    def _get_definition(self, id_: str) -> Definition:
        """ Returns class definition if exists or creates new else """

        if id_ not in self._definition_map:
            if id_ in self._configuration.definition_map:
                class_ = self._configuration.definition_map[id_].class_
            else:
                class_ = dereference(class_qualname=id_)

            self._definition_map[id_] = self._create_definition(id_=id_, class_=class_)

        return self._definition_map[id_]

    def _create_definition(self, class_: type, id_: str = None) -> Definition:
        if id_ is None:
            id_ = reference(id_=class_)

        if id_.lower().endswith('interface'):  # try to autowire interface
            if id_ not in self._configuration.definition_map:
                raise Exception(f'Can not autowire interface `{id_!s}`')

            class_ = self._configuration.definition_map[id_].class_

        constructor = _inspect.signature(class_.__init__)

        if id_ in self._configuration.definition_map:
            definition = self._configuration.definition_map[id_]

            for argument in definition.arguments:  # validate definition
                if argument not in constructor.parameters:
                    raise InvalidDefinitionConfigurationException(
                        f'Invalid definition: parameter `{argument!s}` not found in `{id_!s}`'
                    )

                if constructor.parameters[argument].annotation.__module__ == 'typing':
                    continue  # todo: implement check

                if isinstance(definition.arguments[argument], Reference):
                    # fixme get definition by id and compare with typehint
                    continue

                if not isinstance(definition.arguments[argument], constructor.parameters[argument].annotation):
                    raise InvalidDefinitionConfigurationException(
                        f'Invalid definition: type of `{argument!s}` argument must be '
                        f'`{reference(id_=constructor.parameters[argument].annotation)!s}`, '
                        f'`{reference(definition.arguments[argument])!s}` given.'
                    )
        else:
            definition = Definition(class_=class_, public=True)

        for argument in constructor.parameters:  # autowire
            if argument == 'self':
                continue

            if argument in definition.arguments:
                continue  # skip wired argument (with definition)

            argument_meta = constructor.parameters[argument]

            if argument_meta.kind is _inspect.Parameter.VAR_KEYWORD or argument_meta.kind is _inspect.Parameter.VAR_POSITIONAL:
                continue  # fixme

            if argument_meta.default is not _inspect.Parameter.empty:
                definition.arguments[argument] = argument_meta.default
                continue

            if isinstance(argument_meta.annotation, str):
                """ string annotation case, eg: def __init__(self, argument: 'string_path') """
                if argument_meta.annotation in _builtin_qualname_set:
                    raise Exception('buidfs')  # fixme

                class_path_list = argument_meta.annotation.split('.')
                resolved_class = _inspect.getmodule(class_)

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

            argument_class_qualname = reference(argument_meta.annotation)
            if argument_class_qualname in _builtin_qualname_set:
                raise Exception(
                    f'Unable to create definition `{id_!s}`: unable to autowire `{argument!s}` argument'
                )

            definition.arguments[argument] = Reference(id_=argument_class_qualname)
        return definition
