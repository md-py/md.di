import typing as _typing

import md.di


__all__ = ['resolve']


def _resolve_argument_value(argument_value: _typing.Any):
    if isinstance(argument_value, str):
        if argument_value.startswith(r'\@') or argument_value.startswith('@@'):
            return argument_value[1:]

        if argument_value.startswith('@'):
            return md.di.Reference(id_=argument_value[1:])

        # if isinstance(argument_value, str):
        #     return md.di.Parameter()

    if isinstance(argument_value, list):  # fixme: replace list with iterable
        for argument_key_, argument_value_ in enumerate(argument_value):
            argument_value[argument_key_] = _resolve_argument_value(argument_value=argument_value_)

    # todo dict & other types

    return argument_value


def _resolve_definition_map(services_configuration: dict) -> _typing.Dict[str, md.di.Definition]:
    definition_map = {}

    for id_, definition_configuration in services_configuration.items():
        factory = None
        if 'factory' in definition_configuration:
            factory = definition_configuration['factory']

        class_ = None
        if 'class' in definition_configuration:
            if factory:
                raise Exception('Definition can not contain `class` & `factory` parameters simultaneously')
            class_ = md.di.dereference(class_qualname=definition_configuration['class'])
        elif not factory:
            class_ = md.di.dereference(class_qualname=id_)

        arguments = None
        if 'arguments' in definition_configuration:
            arguments = definition_configuration['arguments']

            for argument in arguments:
                arguments[argument] = _resolve_argument_value(arguments[argument])

        public = False
        if 'public' in definition_configuration:
            public = definition_configuration['public']

        tags = None
        if 'tags' in definition_configuration:
            tags = definition_configuration['tags']

        definition_map[id_] = md.di.Definition(
            class_=class_,
            factory=factory,
            arguments=arguments,
            public=public,
            tags=tags,
        )

    return definition_map


def _validate(configuration: dict) -> None:
    pass


# public API


def resolve(configuration: dict) -> md.di.Configuration:
    """ Creates objective container configuration from scalar """

    _validate(configuration=configuration)

    parameter_map = configuration['parameters']
    definition_map = _resolve_definition_map(services_configuration=configuration['services'])

    return md.di.Configuration(
        parameter_map=parameter_map,
        definition_map=definition_map,
    )
