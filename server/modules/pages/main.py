import formencode
from fastapi import APIRouter, status, Response, Depends, Request
from core.db import SessionManager
from .validator import PageValidator
from core.dependencis import get_current_user
from . import schema
from .tasks import schema as task_schema
from modules.pages.models import Page
from modules.pages.tasks.models import Task
from modules.users.models import User
from modules.pages.tasks.main import router as task_router

router = APIRouter()
router.include_router(
    task_router,
    prefix="/tasks",
)


@router.post("/")
async def create_page(request: Request, response: Response, current_user: User = Depends(get_current_user)):
    try:
        page_dict = await request.json()
        page_dict.update({'author': current_user.id})
        # import pdb;pdb.set_trace()
        clean_data = PageValidator.to_python(page_dict)
        data = Page(**clean_data)
        # session = create_session()
        session = SessionManager.create_session()

        session.add(data)
        # session.rollback()
        session.commit()
        session.refresh(data)
        session.close()
        response.status_code = status.HTTP_201_CREATED
        return {'status': status.HTTP_201_CREATED, 'message': 'Page Created', 'data': data}

    except formencode.Invalid as e:
        response.status_code = status.HTTP_406_NOT_ACCEPTABLE
        return {'status': status.HTTP_406_NOT_ACCEPTABLE, 'message': 'Fix the following error ',
                'error_dict': e.unpack_errors()}

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {'status': status.HTTP_500_INTERNAL_SERVER_ERROR, 'message': 'Internal server error ',
                'error_dict': e}


@router.get("/{page_id}")
def get_page(page_id: int, response: Response, current_user: User = Depends(get_current_user)):
    try:
        session = SessionManager.create_session()
        existing_page = session.query(Page).filter(Page.id == page_id, Page.author == current_user.id).first()
        child_pages = session.query(Page).filter(Page.parent_page_id == page_id, Page.author == current_user.id).all()
        tasks_list = session.query(Task).filter(Task.page_id == page_id, Task.author == current_user.id).all()
        session.close()
        if existing_page is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return {'status': status.HTTP_404_NOT_FOUND, 'message': 'Page not found'}
        page = schema.ReadPage(**existing_page.__dict__)
        children = schema.PageListView(pages=child_pages)
        tasks = task_schema.TaskListView(tasks=tasks_list)
        response.status_code = status.HTTP_200_OK
        return {'status': status.HTTP_200_OK, 'message': 'page details loaded',
                'data': {'page': page, 'children': children.pages, 'tasks': tasks.tasks}}

    except Exception as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'status': status.HTTP_404_NOT_FOUND, 'message': 'Internal server error ', 'error_dict': e}


@router.put("/{page_id}")
async def update_page(request: Request, page_id: int, response: Response,
                      current_user: User = Depends(get_current_user)):
    try:

        session = SessionManager.create_session()
        page_dict = await request.json()
        page_dict.update({'author': current_user.id})
        page_dict = PageValidator.to_python(page_dict)
        existing_page = session.query(Page).filter(Page.id == page_id, Page.author == current_user.id).first()
        if existing_page is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return {'status': status.HTTP_404_NOT_FOUND, 'message': 'Page not found'}

        existing_page.author = page_dict.get('author')
        existing_page.parent_page_id = page_dict.get('parent_page_id')
        existing_page.page_name = page_dict.get('page_name')
        existing_page.page_description = page_dict.get('page_description')
        existing_page.color = page_dict.get('color')
        session.merge(existing_page)

        session.commit()
        session.refresh(existing_page)
        session.close()
        response.status_code = status.HTTP_200_OK
        return {'status': status.HTTP_200_OK, 'message': 'Page Updated', 'data': existing_page}

    except formencode.Invalid as e:
        response.status_code = status.HTTP_406_NOT_ACCEPTABLE
        return {'status': status.HTTP_406_NOT_ACCEPTABLE, 'message': 'Fix the following error ',
                'error_dict': e.unpack_errors()}

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {'status': status.HTTP_500_INTERNAL_SERVER_ERROR, 'message': 'Internal server error ',
                'error_dict': e}


@router.delete("/{page_id}")
def delete_page(page_id: int, response: Response, current_user: User = Depends(get_current_user)):
    try:
        session = SessionManager.create_session()
        existing_page = session.query(Page).filter(Page.id == page_id, Page.author == current_user.id).first()
        if existing_page is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return {'status': status.HTTP_404_NOT_FOUND, 'message': 'Page not found'}

        session.delete(existing_page)
        session.commit()
        session.close()
        response.status_code = status.HTTP_204_NO_CONTENT
        return {'status': status.HTTP_204_NO_CONTENT, 'message': 'Page Deleted'}

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {'status': status.HTTP_500_INTERNAL_SERVER_ERROR, 'message': 'Internal server error ',
                'error_dict': e}
