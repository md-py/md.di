# md.di

md.di is a component that provides dependency injection 
container & tools for python application. 
Inspired by `symfony/dependency-injection`.

## tl; dr 

Briefly, container is for automatically class instantiating.

```python3
import typing


# Email utility contracts
class RenderEmailInterface:
    """ Renders email message for recipient list (just basic example) """
    def for_(self, address_list: typing.List[str]) -> str:
        raise NotImplementedError


class SendEmailInterface:
    """ Sends email message for recipient list (just basic example) """
    def to(self, address_list: typing.List[str], content: str, type_: str = 'text/plain') -> None:
        raise NotImplementedError


# Example implementation
class BlockingSendEmail(SendEmailInterface):
    def to(self, address_list: typing.List[str], content: str, type_: str = 'text/plain') -> None:
        print(f'Email ({content}) has been sent to: ', ','.join(address_list))


# Domain
class Client:
    def __init__(self, id_: str) -> None:
        self.id = id_
        self.email = f'client-{id_!s}@example.net'

    def get_id(self) -> str:
        return self.id

    def get_email(self) -> str:
        return self.email


class ClientRepository:
    def get(self, id_: str) -> Client:
        return Client(id_=id_)


# Domain logic
class RenderWeeklyDigestNewsletterEmail:
    def for_(self, address_list: typing.List[str]) -> str:
        return (
            'To: ' + ','.join(address_list) +
            '\r\n\r\n'
            'Hi, Weekly digest is example'
        )


class SendLetter:
    def __init__(
        self,
        client_repository: ClientRepository,
        render_email: RenderEmailInterface,
        send_email: SendEmailInterface
    ) -> None:
        self._client_repository = client_repository
        self._render_email = render_email
        self._send_email = send_email

    def for_client(self, id_: str) -> None:
        client = self._client_repository.get(id_=id_)
        address_list = [client.get_email()]
        content = self._render_email.for_(address_list=address_list)
        self._send_email.to(address_list=address_list, content=content)


if __name__ == '__main__':
    import md.di

    # Setup container configuration
    configuration = md.di.Configuration(
        definition_map={
            'ClientRepository': md.di.Definition(class_=ClientRepository),
            'RenderWeeklyDigestNewsletterEmail': md.di.Definition(class_=RenderWeeklyDigestNewsletterEmail),
            'BlockingSendEmail': md.di.Definition(class_=BlockingSendEmail),
            'SendLetter.weekly_digest_newsletter': md.di.Definition(
                public=True,
                class_=SendLetter,
                arguments={
                    'client_repository': md.di.Reference(id_='ClientRepository'),
                    'render_email': md.di.Reference(id_='RenderWeeklyDigestNewsletterEmail'),
                    'send_email': md.di.Reference(id_='SendEmailInterface')
                }
            )
        },
        definition_alias_map={
            'SendEmailInterface': 'BlockingSendEmail'
        }
    )

    # Initialize container with configuration
    container = md.di.Container(configuration=configuration)

    # Make action 
    send_weekly_digest_newsletter = container.get(id_='SendLetter.weekly_digest_newsletter')
    assert isinstance(send_weekly_digest_newsletter, SendLetter)

    send_weekly_digest_newsletter.for_client(id_='42')
```

So called `live` container designed to create container configuration
on fly, it's marked for development only and will be replaced
with autowire tools in future release.

```python3
if __name__ == '__main__':
    import md.di.live

    # Initialize container with configuration
    container = md.di.live.Container(configuration=None)

    # Make action 
    send_weekly_digest_newsletter = container.get(id_='SendLetter.weekly_digest_newsletter')
    assert isinstance(send_weekly_digest_newsletter, SendLetter)

    send_weekly_digest_newsletter.for_client(id_='42')
```

## [Documentation](docs/index.md)

## Features

| Feature                | Support                                           |
|------------------------|---------------------------------------------------|
| Container compilation  | No (but configuration processing)                 |
| Definition decorator   | No (support is not planned)                       |
| Definition inheritance | No (support is not planned)                       |
| Lazy service           | No                                                |
| Abstract service       | No (support is not planned)                       |
| Expression language    | No (support is not planned)                       |
| Thread-Safe            | Not yet                                           |
| Service factory        | Yes                                               |
| Autowiring             | Partly (via `live` container), support is planned |


## Strategy (Roadmap)

- few container instances support
- cache
- unit test coverage
- `typing` annotation support
- refuse from `inspect` module 
- internal configuration processor
  - circular reference  
- thread-safe container
- ... and many other

## Status

Current status: development preview. not for production usage.

## [License (MIT)](license.md)
