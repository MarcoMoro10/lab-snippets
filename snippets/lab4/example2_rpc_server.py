from snippets.lab3 import Server
from snippets.lab4.users.impl import *
from snippets.lab4.example1_presentation import serialize, deserialize, Request, Response
from snippets.lab4.users import Role
import traceback
import logging

# Configura il logger
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



class ServerStub(Server):
    def __init__(self, port):
        super().__init__(port, self.__on_connection_event)
        self.__user_db = InMemoryUserDatabase()
        self.__auth_service= InMemoryAuthenticationService(self.__user_db)
    
    def __on_connection_event(self, event, connection, address, error):
        match event:
            case 'listen':
                print('Server listening on %s:%d' % address)
            case 'connect':
                connection.callback = self.__on_message_event
            case 'error':
                traceback.print_exception(error)
            case 'stop':
                print('Server stopped')
    
    def __on_message_event(self, event, payload, connection, error):
        match event:
            case 'message':
                print('[%s:%d] Open connection' % connection.remote_address)
                request = deserialize(payload)
                assert isinstance(request, Request)
                print('[%s:%d] Unmarshall request:' % connection.remote_address, request)
                response = self.__handle_request(request)
                connection.send(serialize(response))
                print('[%s:%d] Marshall response:' % connection.remote_address, response)
                connection.close()
            case 'error':
                traceback.print_exception(error)
            case 'close':
                print('[%s:%d] Close connection' % connection.remote_address)
    
    def __handle_request(self, request: Request) -> Response:
  
        logger.debug(f"Handling request: {request}")
    
        try:
            if request.name == "get_user":
                if not request.metadata:
                    raise PermissionError("Missing metadata for authorization.")
                if request.metadata.user.role != Role.ADMIN:
                    raise PermissionError("You are not authorized to perform this operation.")
                if not self.__auth_service.validate_token(request.metadata):
                    raise PermissionError("Invalid or expired token.")

            if hasattr(self.__user_db, request.name):
                method = getattr(self.__user_db, request.name)
                target_service = "UserDatabase"
            elif hasattr(self.__auth_service, request.name):
                method = getattr(self.__auth_service, request.name)
                target_service = "AuthenticationService"
            else:
                raise AttributeError(f"Method '{request.name}' not found in available services.")

            logger.debug(f"Found method '{request.name}' in {target_service}.")

            logger.debug(f"Executing method '{request.name}' with arguments: {request.args}.")
            result = method(*request.args)

            logger.info(f"Method '{request.name}' executed successfully with result: {result}.")
            return Response(result=result, error=None)

        except PermissionError as e:
            error_message = f"Permission denied: {e}"
            logger.warning(error_message)
            return Response(result=None, error=error_message)

        except AttributeError as e:
            error_message = f"Invalid method: {e}"
            logger.error(error_message)
            return Response(result=None, error=error_message)

        except Exception as e:
            error_message = f"Unexpected error occurred: {traceback.format_exc()}"
            logger.error(error_message)
            return Response(result=None, error=error_message)


if __name__ == '__main__':
    import sys
    server = ServerStub(int(sys.argv[1]))
    while True:
        try:
            input('Close server with Ctrl+D (Unix) or Ctrl+Z (Win)\n')
        except (EOFError, KeyboardInterrupt):
            break
    server.close()