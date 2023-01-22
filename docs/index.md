# Documentation

!!! warning

    Current implementation is under development,
    consider to avoid using it in production until 1.0.0

## Overview

md.di component provides dependency injection container
designed for automatically class instantiating and centralization
the way objects are constructed.

Implementation provides 
[constructor](#constructor-injection), 
[property](#property-injection), 
[setter](#setter-injection) types of dependency injection,
[service factory](#service-factory), container configuration 
[dynamic processing](../md.di.configuration/), 
[persistence](../md.di.persistence/) and etc.

## Architecture overview

![Architecture overview](_static/architecture-overview.class-diagram.svg)

Terminology:

- *service* — any class instance retrieved from service container 
- *[service definition](#service-definition)* — instruction how to initialize service 
  (class instance); contains constructor arguments, 
  list of [methods calls](#method-call-and-setter-injection), etc. 
  part of *container configuration* 
- *service definition reference* — reference to existing definition, 
  used to define dependency for concrete service definition; represents basic DTO.
- *service container* — dependency injection container implementation instance,
  contains service instantiating logic
- *[container configuration](#constructor-configuration)* — contains set of definitions,
  definition [aliases](#service-alias), and [parameters](#container-parameters) 


!!! note

    Due to following [single responsibility principle](https://en.wikipedia.org/wiki/Single-responsibility_principle)
    **md.di** component does not provides container configuration persistence, 
    processing, etc out of box. Container (`md.di.Container`) assumes works with completed 
    [container configuration](#container-configuration).
    All related features are decoupled into independent components 


## Installation

```sh
pip install md.di --index-url https://source.md.land/python/
```

## Usage example

For example, typical code without dependency injection container would look like:

```python3 linenums="1" hl_lines="12"
#!/usr/bin/env python3
class Greeter:
    def __init__(self, name: str = 'Greeter') -> None:
        self._name = name

    def greet(self, who: str) -> str:
        return f'{self._name} greets {who}'


if __name__ == '__main__':
    # arrange
    greeter = Greeter()

    # act
    print(greeter.greet('demo example'))
```

The simplest case of dependency injection container usage is contain
of configuration is a service without parameters at all, it looks like:

```python3 linenums="10"  hl_lines="2 5-13"
if __name__ == '__main__':
    import md.di

    # arrange
    container_configuration = md.di.Configuration(
        definition_map={
            'Greeter': md.di.Definition(
                class_=Greeter,
                public=True,  # (1)
            ),
        },
    )
    container = md.di.Container(configuration=container_configuration)

    # act
    greeter = container.get(id_='Greeter')  # (2)
    assert isinstance(greeter, Greeter)
    print(greeter.greet('demo example'))
```

1. Majority number of services does not require to be retrieved 
   within related `container.get` method call, otherwise
   [service definition visibility](#service-visibility) option should
   be passed explicitly

2. When code entity loaded, it could be passed as a service identifier as is:
   `container.get(id_=Greeter)`;
   otherwise string value could be passed: `container.get(id_='Greeter')`

!!! warning

    In example above there is no configuration validation,
    so invalid setup (eg. service circular reference) may cause error at runtime. 
    To enable configuration validation, consider to use 
    to [md.di.configuration](../md.di.configuration/#validate-container-configuration) 
    component.


## Service definition
### Constructor configuration

To configure service constructor parameter `arguments` argument value should be provided:   

```python3 linenums="14" hl_lines="5-7"
    container_configuration = md.di.Configuration(
        definition_map={
            'Greeter': md.di.Definition(
                class_=Greeter, 
                arguments={
                    'name': 'Parametrized greeter',
                },
                public=True,
            ),
        },
    )
```

#### Constructor injection

=== "Basic example"

    ```python3
    #!/usr/bin/env python3
    class Greeter:
        def __init__(self, name: str = 'Greeter') -> None:
            self._name = name
    
        def greet(self, who: str) -> str:
            return f'{self._name} greets {who}'
    
    
    if __name__ == '__main__':
        import md.di
    
        # arrange
        container_configuration = md.di.Configuration(
            definition_map={
                'Greeter': md.di.Definition(
                    class_=Greeter,
                    public=True,  # (1)
                ),
            },
        )
        container = md.di.Container(configuration=container_configuration)
    
        # act
        greeter = container.get(id_='Greeter')  # (2)
        assert isinstance(greeter, Greeter)
        print(greeter.greet('demo example'))
    ```

=== "Advanced example"

    TODO


If service requires to be build depending on runtime
take a look for [md.di.configuration / definition argument processing](../md.di.configuration/#resolve-definition-arguments)

### Method call

Service may require a call to it, to be finally initialized,
for example:

- dependency injection case
  - to solve circular reference issue
  - to keep constructor signature backward compatibility when 
    new dependency or option added in version (that not requires major version increment)  
- service initialization

```python3
import md.di

class Greeter:
    def __init__(self, name: str = 'Greeter') -> None:
        self._name = name
        self._greeting = 'Hello'

    def set_greeting(self, greeting: str) -> None:
        self._greeting = greeting
        
    def greet(self, who: str) -> str:
        return f'{self._name} greets {who}: {self._greeting}'

container_configuration = md.di.Configuration(
  definition_map={
    'Greeter': md.di.Definition(
      class_=Greeter,
      calls=[
        (
            'set_greeting',  # method name
            [],  # *args 
            {'greeting': 'hi'}  # **kwargs
        ),
        # or:
        # ('set_greeting', ['hi'], {})
      ])
  },
)
```

#### Setter injection

#### Property injection

Implementation of property injection is special kind of setter injection, 
realized with magic `__setattr__` method call.

```python3
import md.di

container_configuration = md.di.Configuration(
  definition_map={
    'Greeter': md.di.Definition(
      class_=Greeter,
      calls=[
        (
            '__setattr__',  # method name
            [],  # *args 
            {'name': 'property_name', 'value': 'property_value'}  # **kwargs
        ),
        # or:
        # ('__setattr__', ['property_name', 'property_value'], {})
      ])
  },
)
```

### Service visibility

Every service defined is private by default.
When a service is private, it cannot be accessed directly from 
the container using `container.get()`. 

As a best practice, it should only be created private 
services and fetch services using dependency
injection instead of using `container.get()`.

### Service sharing

Dependency injection container assumes to reuse service instances since it created,
e.g. when few services depends on other, since it instance instantiated it will be 
injected into first services.

This practice requires to design services [clean](#) and [stateless](#),
and also thread-safe for multithreading applications.

TODO EXAMPLE

By default, each service is shared.
When service is required to be instantiated each time on demand, 
then related service definition `shared` option should be set to `True`, e.g.

TODO USE-CASES


```python3
import md.di

definition = md.di.Definition(
    factory=lambda: open('/dev/stderr'),
    shared=False,
)
```

### Service factory

- function
- service method invocation

## Synthetic service

Synthetic service is a service added in runtime after
container instance initialized, such services may have no definition.

```python3 linenums="1" hl_lines="13 16"
class Example:
    pass


if __name__ == '__main__':
    import md.di

    # arrange
    container_configuration = md.di.Configuration()
    container = md.di.Container(configuration=container_configuration)

    # act
    synthetic_service = Example()
    assert not container.has(id_=Example) 
    
    container.set(id_=Example, instance=synthetic_service)
    
    synthetic_service_ = container.get(id_=Example)
    assert synthetic_service is synthetic_service_ 
```

!!! note
    
    Contract `psr.container.ContainerInterface` has no `set` method,
    but only `md.di.Container`; in some cases related instance check 
    may be required, eg.

    ```python3  hl_lines="2"
    def inject_instances(container: psr.container.ContainerInterface) -> None:
        if not isinstance(container, md.di.Container):
            raise NotImplementedError(f'Unable to set synthetic service into `{type(container)!s}`')

        # call `container.set()` method ...
    ```


## Container configuration

Container configuration represents simple data structure
containing maps of parameters, 
[service definition](#service-definition) and
[service definition alias](#service-alias).

![container configuration parts class diagram](_static/container-configuration.class-diagram.svg)

!!! note

    Container configuration designed to be passed into container
    before container could be used, so at that moment configuration 
    is expected to be processed and valid.

!!! warning

    md.di component has no configuration validation out from box,
    so invalid setup (eg. service circular reference) may cause error at runtime. 
    To enable configuration validation, consider to use 
    to [md.di.configuration](../md.di.configuration/#validate-container-configuration) 
    component.

### Container parameters (WIP)

Some services require to be configured with parameter,
and parameter values may be different depending on application 
environment (for example) 

```python3
import sqlalchemy 
engine = sqlalchemy.create_engine('postgresql://scott:tiger@localhost:5432/mydatabase')
```

### Service alias

```python3
import md.di

container_configuration = md.di.Configuration(
    definition_map={
        'Greeter': md.di.Definition(
            class_=Greeter,
        )
    },
    definition_alias_map={
        'Greeter_alias': 'Greeter'
    },
)
```

#### Default contract implementation

TODO
