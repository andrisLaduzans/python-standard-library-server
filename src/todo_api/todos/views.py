from http import HTTPStatus

from todo_api.http_layer.http_request import HttpRequest
from todo_api.http_layer.http_response import HttpResponse
from todo_api.http_layer.router import Routes
from todo_api.todos.todo import TodoField
from todo_api.todos.todo_schemas import (
    TodoCreateRequest,
    TodoListQuery,
    TodoUpdateRequest,
)
from todo_api.todos.todo_service import TodoService


class TodoViews:
    def __init__(self, service: TodoService) -> None:
        self._service = service

    def list_todos(self, request: HttpRequest, _: dict[str, str]) -> HttpResponse:
        query = TodoListQuery.from_query_params(request.query)
        todos = self._service.get_all(
            is_done=query.is_done,
            limit=query.limit,
            offset=query.offset,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            search=query.search,
            owner_id=request.require_user_id(),
        )
        return HttpResponse.json(HTTPStatus.OK, todos)

    def get_todo(self, request: HttpRequest, params: dict[str, str]) -> HttpResponse:
        todo = self._service.find_by_id(
            params[TodoField.ID], owner_id=request.require_user_id()
        )
        return HttpResponse.json(HTTPStatus.OK, todo)

    def create_todo(self, request: HttpRequest, _: dict[str, str]) -> HttpResponse:
        data = TodoCreateRequest.from_dict(request.json())
        todo = self._service.create(
            data.name, data.description, owner_id=request.require_user_id()
        )
        return HttpResponse.json(
            HTTPStatus.CREATED, todo, {"Location": Routes.Todos.with_id(todo["id"])}
        )

    def update_todo(self, request: HttpRequest, params: dict[str, str]) -> HttpResponse:
        data = TodoUpdateRequest.from_dict(request.json())
        todo = self._service.update_todo(
            params[TodoField.ID], data, owner_id=request.require_user_id()
        )
        return HttpResponse.json(HTTPStatus.OK, todo)

    def delete_todo(self, request: HttpRequest, params: dict[str, str]) -> HttpResponse:
        todo = self._service.delete(
            params[TodoField.ID], owner_id=request.require_user_id()
        )
        return HttpResponse.json(HTTPStatus.OK, todo)
