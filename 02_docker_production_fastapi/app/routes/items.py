"""CRUD endpoints for the Item resource."""

import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas import Item, ItemCreate
from app.storage import ItemStore

logger = logging.getLogger("app.items")

router = APIRouter(prefix="/items", tags=["items"])


def get_store(request: Request) -> ItemStore:
    """Fetch the shared ItemStore instance from application state."""
    return request.app.state.store


@router.post("", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, request: Request) -> Item:
    store = get_store(request)
    item = Item.new(payload)
    store.add_item(item)
    logger.info("Created item %s", item.id)
    return item


@router.get("", response_model=list[Item])
def list_items(request: Request) -> list[Item]:
    return get_store(request).list_items()


@router.get("/{item_id}", response_model=Item)
def get_item(item_id: str, request: Request) -> Item:
    item = get_store(request).get_item(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: str, request: Request) -> None:
    deleted = get_store(request).delete_item(item_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
