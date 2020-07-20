import re as _re
import typing as _typing

import psr.container

import md.di


class ParameterCircularReferenceException(psr.container.ContainerExceptionInterface):
    pass


class ParameterNotFoundException(psr.container.ContainerExceptionInterface):
    pass


class ConfigurationProcessor:
    """ Processes container configuration: resolves parameter map values and definition arguments """
    def __init__(self):
        self._loading_parameter_list: _typing.List[str] = []

    def process(self, configuration: md.di.Configuration) -> md.di.Configuration:
        processed_configuration = md.di.Configuration()
        processed_configuration.parameter_map = configuration.parameter_map
        processed_configuration.definition_map = configuration.definition_map

        for parameter_key in processed_configuration.parameter_map:
            processed_configuration.parameter_map[parameter_key] = self._resolve_parameter_value(
                parameter_value=processed_configuration.parameter_map[parameter_key],
                parameter_map=processed_configuration.parameter_map,
            )

        for definition_id in processed_configuration.definition_map:
            for argument_key, argument_value in processed_configuration.definition_map[definition_id].arguments.items():
                if isinstance(argument_value, str):
                    processed_configuration.definition_map[definition_id].arguments[argument_key] = self._resolve_parameter_value(
                        parameter_value=argument_value,
                        parameter_map=processed_configuration.parameter_map,
                    )

        return processed_configuration

    def _resolve_parameter_value(self, parameter_value: str, parameter_map: dict) -> str:
        for match in _re.finditer(r'(?P<parameter>(?<!%)%(?P<parameter_id>[^%]+)%)', parameter_value):
            match_map: dict = match.groupdict()

            resolved_parameter = self._create_parameter(id_=match_map['parameter_id'], parameter_map=parameter_map)
            if not isinstance(resolved_parameter, str):
                raise NotImplementedError

            parameter_value = parameter_value.replace(match_map['parameter'], resolved_parameter)

        return parameter_value

    def _create_parameter(self, id_: str, parameter_map: dict) -> _typing.Any:
        if id_ in self._loading_parameter_list:
            raise ParameterCircularReferenceException(f'The parameter `{id_!s}` has a circular reference to itself.')

        if id_ not in parameter_map:
            raise ParameterNotFoundException(f'The parameter definition `{id_!s}` does not exist.')

        self._loading_parameter_list.append(id_)

        parameter = self._resolve_parameter_value(
            parameter_value=parameter_map[id_],
            parameter_map=parameter_map
        )

        self._loading_parameter_list.pop()

        return parameter


class ConfigurationBuilder:
    def __init__(
            self,
            configuration: md.di.Configuration,
            compiler_pass_list: _typing.List['BuilderPassInterface'],
    ):
        self.configuration: md.di.Configuration = configuration
        self._compiler_pass_list: _typing.List['BuilderPassInterface'] = compiler_pass_list

        self._is_built = False

    def build(self) -> None:
        if self._is_built:
            return

        for compiler_pass in self._compiler_pass_list:
            compiler_pass.process(configuration_builder=self)

        self.configuration = ConfigurationProcessor().process(configuration=self.configuration)

        self._is_built = True

    def find_tagged_definitions(self, tag: str) -> _typing.Dict[str, md.di.Definition]:
        definition_map = {}

        for id_, definition in self.configuration.definition_map.items():
            if definition.has_tag(tag=tag):
                definition_map[id_] = definition

        return definition_map

    def get_definition(self, id_: _typing.Union[str, type]) -> _typing.Union[md.di.Definition, None]:
        id_ = md.di.reference(id_=id_)

        if id_ in self.configuration.definition_map:
            return self.configuration.definition_map[id_]
        return None

    def get_parameter(self, name: str) -> _typing.Any:  # fixme RTH
        if name in self.configuration.parameter_map:
            return self.configuration.parameter_map[name]
        return None


class BuilderPassInterface:  # Compiler pass
    """ Defines contract to modify container configuration on build phase """
    def process(self, configuration_builder: 'ConfigurationBuilder') -> None:
        raise NotImplementedError
